"""Download a small, deterministic Open Images subset for vision tests/eval.

Usage (from model-service/):  python eval/prepare_images.py [--per-folder 30]
Output: data/images/<folder>/<split>_<ImageID>.jpg   (data/ is git-ignored)

Open Images has no usable class for takeout food packaging or cooler bags, so
data/images/package_food/ and package_cooler/ are created empty for photos the
team takes itself. Plastic bags are rare, so both validation and test splits are used.
"""

import argparse
import csv
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"
CACHE = BASE / "openimages"
OUT = BASE / "images"
SPLITS = ("validation", "test")
BBOX_URL = "https://storage.googleapis.com/openimages/v5/{}-annotations-bbox.csv"
IMAGE_URL = "https://open-images-dataset.s3.amazonaws.com/{}/{}.jpg"

PEOPLE = {"/m/01g317", "/m/04yx4", "/m/03bt1vf", "/m/01bl7v", "/m/05r655"}  # Person, Man, Woman, Boy, Girl
BOX, PLASTIC_BAG, DOOR = "/m/025dyy", "/m/05gqfk", "/m/02dgv"
DOG, CAT = "/m/0bt9lr", "/m/01yrx"
PACKAGE_LIKE = {BOX, PLASTIC_BAG, "/m/011q46kg", "/m/0hf58v5", "/m/080hkjn", "/m/01940j"}  # + container, bags, handbag, backpack

# folder -> (classes that must be present, min box area fraction, classes that must be absent)
FOLDERS = {
    "person": (PEOPLE, 0.10, set()),
    "package_box": ({BOX}, 0.05, PEOPLE),
    "package_bag": ({PLASTIC_BAG}, 0.02, PEOPLE),
    "empty": ({DOOR}, 0.10, PEOPLE | PACKAGE_LIKE),
    "animal": ({DOG, CAT}, 0.10, PEOPLE | PACKAGE_LIKE),
}
TEAM_PHOTO_FOLDERS = ("package_food", "package_cooler")


def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest)
    return dest


def load_boxes() -> dict[tuple[str, str], list[tuple[str, float]]]:
    """(split, ImageID) -> [(LabelName, box area fraction)], skipping drawings/depictions."""
    boxes = defaultdict(list)
    for split in SPLITS:
        path = fetch(BBOX_URL.format(split), CACHE / f"{split}-annotations-bbox.csv")
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["IsDepiction"] == "1":
                    continue
                area = (float(row["XMax"]) - float(row["XMin"])) * (float(row["YMax"]) - float(row["YMin"]))
                boxes[(split, row["ImageID"])].append((row["LabelName"], area))
    return boxes


def select(boxes, required: set[str], min_area: float, forbidden: set[str], n: int):
    chosen = []
    for key in sorted(boxes):
        labels = boxes[key]
        if any(label in forbidden for label, _ in labels):
            continue
        if any(label in required and area >= min_area for label, area in labels):
            chosen.append(key)
            if len(chosen) == n:
                break
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-folder", type=int, default=30)
    args = parser.parse_args()

    boxes = load_boxes()
    for folder in TEAM_PHOTO_FOLDERS:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    for folder, (required, min_area, forbidden) in FOLDERS.items():
        keys = select(boxes, required, min_area, forbidden, args.per_folder)
        for split, image_id in keys:
            fetch(IMAGE_URL.format(split, image_id), OUT / folder / f"{split}_{image_id}.jpg")
        print(f"{folder}: {len(keys)} images")


if __name__ == "__main__":
    main()
