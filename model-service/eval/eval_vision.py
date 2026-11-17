"""Vision hit rates per image folder (data/images/<folder>/*.jpg, from eval/prepare_images.py + team photos).

False alarms are measured on two folders without packages or people: empty (hallways, 30) and
hard_negative (150 Open Images validation photos of bags, suitcases and doors — the harder case;
copy them from the fine-tuning data: DATA_ROOT/eval negatives, see eval/README 2026-11-17 Q4).

Usage (from model-service/):  python -m eval.eval_vision
"""

from collections import Counter

from PIL import Image

from app.config import DATA_DIR, Settings
from eval.metrics import TARGETS, verdict

# folder -> label that should be found there
EXPECTED = {"person": "person", "package_box": "package", "package_bag": "package",
            "package_food": "package", "package_cooler": "package", "animal": "animal"}
NEGATIVE_FOLDERS = ("empty", "hard_negative")


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
    print("\n| 오탐 세트 | 장수 | 무엇이든 | 물품 | 사람 | 물품 오탐 출처 |\n|---|---:|---:|---:|---:|---|")
    for folder in NEGATIVE_FOLDERS:
        files = sorted((images / folder).glob("*.jpg"))
        if not files:
            print(f"| {folder} | 0 | — | — | — | 사진 없음 |")
            continue
        anything = package = person = 0
        sources: Counter[str] = Counter()
        for f in files:
            picture = Image.open(f).convert("RGB")
            labels = {d.label for d in vision.detect(picture)}
            anything += bool(labels)
            person += "person" in labels
            if "package" in labels:
                package += 1
                sources.update(package_sources(vision, settings, picture))
        n = len(files)
        top = ", ".join(f"{k} {v}" for k, v in sources.most_common(4)) or "—"
        print(f"| {folder} | {n} | {anything / n:.0%} | {package / n:.0%} | {person / n:.0%} | {top} |")


def package_sources(vision, settings, picture) -> set[str]:
    """Which package model / prompt fired: 'ft:<class>' for the fine-tuned model, else the zero-shot prompt."""
    found = set()
    runs = [("zs", vision.package_model, settings.package_conf)]
    if vision.package_ft_model is not None:
        runs.insert(0, ("ft", vision.package_ft_model, settings.package_ft_conf))
    for tag, model, conf in runs:
        r = model.predict(picture, conf=conf, agnostic_nms=True, quantize=16, verbose=False)[0]
        found |= {f"{tag}:{r.names[int(c)]}" for c in r.boxes.cls}
    return found

if __name__ == "__main__":
    main()
