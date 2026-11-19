"""Q2: person recall vs. false "person" on photos without people, across confidence thresholds.

Runs the service's person model once per photo at a low threshold, keeps the highest person score,
then sweeps the threshold. Positives: data/images/person. Negatives: every other folder (empty
hallways, packages, animals) — a "person" there would wrongly start a reception. hard_negative is left
out: about 21% of it shows real people carrying bags (eval/README.md, Q4).

Usage (from model-service/, GPU):  python -m eval.eval_person_threshold
"""

from PIL import Image

from app.config import DATA_DIR, Settings

THRESHOLDS = (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5)
FLOOR = 0.05
NOT_NEGATIVE = ("person", "hard_negative")


def best_person_scores(vision, files) -> list[float]:
    from app.vision.yolo import COCO_PERSON

    scores = []
    for f in files:
        r = vision.person_model.predict(Image.open(f).convert("RGB"), classes=[COCO_PERSON], conf=FLOOR,
                                        quantize=16, verbose=False)[0]
        scores.append(max((float(c) for c in r.boxes.conf), default=0.0))
    return scores


def main() -> None:
    from app.vision.yolo import YoloVision

    settings = Settings()
    vision = YoloVision(settings)
    images = DATA_DIR / "images"
    pos = best_person_scores(vision, sorted((images / "person").glob("*.jpg")))
    neg_files = sorted(f for d in images.iterdir() if d.is_dir() and d.name not in NOT_NEGATIVE for f in d.glob("*.jpg"))
    neg = best_person_scores(vision, neg_files)

    print(f"## 사람 기준값 곡선 — 사람 사진 {len(pos)}장, 사람 없는 사진 {len(neg)}장 (지금 기준값 {settings.person_conf})\n")
    print("| 기준값 | 사람 찾음 | 사람 없는 사진에서 '사람' |\n|---:|---:|---:|")
    for t in THRESHOLDS:
        hit = sum(s >= t for s in pos)
        false = sum(s >= t for s in neg)
        mark = " ← 지금" if abs(t - settings.person_conf) < 1e-9 else ""
        print(f"| {t:.2f}{mark} | {hit}/{len(pos)} ({hit / len(pos):.0%}) | {false}/{len(neg)} ({false / len(neg):.0%}) |")
    missed = sorted(round(s, 2) for s in pos if s < settings.person_conf)
    print(f"\n지금 기준값에서 놓친 사람 사진의 최고 점수: {missed}")
    top_false = sorted((round(s, 2) for s in neg if s >= FLOOR), reverse=True)[:5]
    print(f"사람 없는 사진의 가장 높은 '사람' 점수: {top_false}")


if __name__ == "__main__":
    main()
