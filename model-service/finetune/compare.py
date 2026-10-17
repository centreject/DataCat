"""Current zero-shot YOLOE vs fine-tuned vs both together: package hit rate, false alarms, speed.

Usage (from model-service/):  python -u finetune/compare.py DATA_ROOT WEIGHTS.pt [conf ...]
Sets: DATA_ROOT/eval (Open Images validation, by class) + data/images package_box/package_bag/empty.
"Zero-shot" uses Settings().package_prompts; set PACKAGE_PROMPTS='[...]' to try another list
(e.g. only the items the fine-tuned model does not know).
"""

import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import DATA_DIR, Settings  # noqa: E402
from app.vision.yolo import YoloVision  # noqa: E402  (also sets Ultralytics env)
from ultralytics import YOLOE  # noqa: E402

NAMES = ["box", "envelope", "plastic bag"]


def sets(ev: Path):
    out = defaultdict(list)
    for img in sorted((ev / "images/train").glob("*.jpg")):
        lab = (ev / "labels/train" / f"{img.stem}.txt").read_text().splitlines()
        cls = {int(line.split()[0]) for line in lab if line.strip()}
        if not cls:
            out["OI 음성(가방·문 등)"].append(img)
        for c in cls:
            out[f"OI {NAMES[c]}"].append(img)
    for f in ("package_box", "package_bag", "empty"):
        out[f"기존 {f}"] = sorted((DATA_DIR / "images" / f).glob("*.jpg"))
    return out


def run(model, paths, **kw):
    """-> ({path: found anything}, median ms). Same predict options as app/vision/yolo.py."""
    model.predict(str(paths[0]), verbose=False, **kw)  # warm-up
    hit, ms = {}, []
    for p in paths:
        t = time.perf_counter()
        hit[p] = len(model.predict(str(p), agnostic_nms=True, quantize=16, verbose=False, **kw)[0].boxes) > 0
        ms.append((time.perf_counter() - t) * 1000)
    return hit, statistics.median(ms)


def main():
    ev, weights = Path(sys.argv[1]) / "eval", sys.argv[2]
    confs = [float(c) for c in sys.argv[3:]] or [0.4]
    s = Settings()
    data = sets(ev)
    paths = sorted({p for ps in data.values() for p in ps})
    zero, zero_ms = run(YoloVision(s).package_model, paths, conf=s.package_conf)
    ft = YOLOE(weights)
    res = {c: run(ft, paths, conf=c) for c in confs}
    print(f"프롬프트 {len(s.package_prompts)}개, 사진 {len(paths)}장, 한 장 중앙값: zero-shot {zero_ms:.1f}ms, "
          + ", ".join(f"학습 c{c} {m:.1f}ms" for c, (_, m) in res.items()) + "\n")
    print("| 세트 | 장수 | zero-shot | " + " | ".join(f"학습 c{c} | 함께 c{c}" for c in confs) + " |")
    print("|" + "---|" * (3 + 2 * len(confs)))
    for name, ps in data.items():
        row = [name, str(len(ps)), f"{sum(zero[p] for p in ps) / len(ps):.0%}"]
        for hit, _ in res.values():
            row += [f"{sum(hit[p] for p in ps) / len(ps):.0%}", f"{sum(hit[p] or zero[p] for p in ps) / len(ps):.0%}"]
        print("| " + " | ".join(row) + " |")
    print("\n음성·empty 줄은 낮을수록 좋음(오탐), 나머지는 높을수록 좋음.")


if __name__ == "__main__":
    main()
