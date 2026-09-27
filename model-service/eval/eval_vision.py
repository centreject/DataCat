"""Vision hit rates per image folder (data/images/<folder>/*.jpg, from eval/prepare_images.py + team photos).

Usage (from model-service/):  python -m eval.eval_vision
"""

from PIL import Image

from app.config import DATA_DIR, Settings
from eval.metrics import TARGETS, verdict

# folder -> label that should be found there
EXPECTED = {"person": "person", "package_box": "package", "package_bag": "package",
            "package_food": "package", "package_cooler": "package"}


def main() -> None:
    from app.vision.yolo import YoloVision

    settings = Settings()
    vision = YoloVision(settings)
    images = DATA_DIR / "images"
    print(f"## 이미지 인식 — person_conf {settings.person_conf}, package_conf {settings.package_conf}\n")
    print("| 폴더 | 이미지 수 | 찾은 비율 | 목표 |\n|---|---:|---:|---|")
    for folder, label in EXPECTED.items():
        files = sorted((images / folder).glob("*.jpg"))
        if not files:
            print(f"| {folder} | 0 | — | 사진 없음 |")
            continue
        hits = sum(any(d.label == label for d in vision.detect(Image.open(f).convert("RGB"))) for f in files)
        rate = hits / len(files)
        target = TARGETS[f"{label}_recall"]
        print(f"| {folder} | {len(files)} | {rate:.0%} | ≥ {target:.0%} {verdict(rate >= target)} |")
    empty = sorted((images / "empty").glob("*.jpg"))
    if empty:
        false_hits = sum(bool(vision.detect(Image.open(f).convert("RGB"))) for f in empty)
        print(f"| empty (오탐) | {len(empty)} | {false_hits / len(empty):.0%} | 낮을수록 좋음 |")


if __name__ == "__main__":
    main()
