"""Build a YOLO dataset for package fine-tuning from Open Images (train split only for training).

  train/: from oidv6 train split   -> used for training (90%) + training-time val (10%)
  eval/:  from v5 validation split -> held-out eval, never trained on; skips images already in
          model-service/data/images (those came from validation/test too).
Classes: 0 box, 1 envelope, 2 plastic bag. Negatives = handbag/suitcase/luggage/door with no package.
Usage (from model-service/):  python -I finetune/prep.py DATA_ROOT   (e.g. ~/oi-data; needs ~3.5 GB)
DATA_ROOT/csv/ must hold train-bbox.csv (v6 oidv6-train-annotations-bbox.csv) and val-bbox.csv
(v5 validation-annotations-bbox.csv) from storage.googleapis.com/openimages. Selection is deterministic.
"""

import csv
import hashlib
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(sys.argv[1])
TARGETS = {"/m/025dyy": 0, "/m/0frqm": 1, "/m/05gqfk": 2}
NAMES = ["box", "envelope", "plastic bag"]
NEG = {"/m/080hkjn", "/m/01s55n", "/m/0hf58v5", "/m/02dgv"}  # handbag, suitcase, luggage&bags, door
MIN_AREA = 0.01
TRAIN_CAP = {0: 1600, 1: 900, 2: 900, "neg": 800}
EVAL_CAP = {0: 150, 1: 100, 2: 100, "neg": 150}
URL = "https://open-images-dataset.s3.amazonaws.com/{}/{}.jpg"
EXISTING = {p.stem.split("_", 1)[-1] for p in (Path(__file__).resolve().parents[1] / "data/images").rglob("*.jpg")}


def scan(path):
    boxes, bad, neg = defaultdict(list), set(), set()
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            i, lab = r["ImageID"], r["LabelName"]
            if lab in NEG:
                neg.add(i)
            if lab not in TARGETS:
                continue
            if r["IsDepiction"] == "1" or r["IsGroupOf"] == "1":
                bad.add(i)
                continue
            x0, x1, y0, y1 = (float(r[k]) for k in ("XMin", "XMax", "YMin", "YMax"))
            boxes[i].append((TARGETS[lab], (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    return boxes, bad, neg


def pick(boxes, bad, neg, cap, skip=frozenset()):
    key = lambda i: hashlib.md5(i.encode()).hexdigest()  # deterministic shuffle
    chosen, count = {}, defaultdict(int)
    for i in sorted(boxes, key=key):
        if i in bad or i in skip:
            continue
        bs = boxes[i]
        if max(w * h for _, _, _, w, h in bs) < MIN_AREA:
            continue
        cls = {c for c, *_ in bs}
        need = [c for c in cls if count[c] < cap[c]]
        if not need:
            continue
        chosen[i] = bs
        for c in cls:
            count[c] += 1
    negs = [i for i in sorted(neg - boxes.keys() - bad - skip, key=key)][: cap["neg"]]
    for i in negs:
        chosen[i] = []
    print(dict(count), "neg", len(negs), "total", len(chosen))
    return chosen


def fetch(args):
    split, i, dest = args
    if dest.exists():
        return True
    try:
        with urllib.request.urlopen(URL.format(split, i), timeout=30) as r:
            dest.write_bytes(r.read())
        return True
    except Exception:
        return False


def write(chosen, split, out, val_every=0):
    jobs = []
    for n, (i, bs) in enumerate(sorted(chosen.items())):
        sub = "val" if val_every and n % val_every == 0 else "train"
        (out / "images" / sub).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sub).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sub / f"{i}.txt").write_text("".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for c, x, y, w, h in bs))
        jobs.append((split, i, out / "images" / sub / f"{i}.jpg"))
    with ThreadPoolExecutor(16) as ex:
        ok = list(ex.map(fetch, jobs))
    for (s, i, dest), good in zip(jobs, ok):  # drop labels of images that failed to download
        if not good:
            Path(str(dest).replace("/images/", "/labels/")).with_suffix(".txt").unlink(missing_ok=True)
    print(split, "downloaded", sum(ok), "/", len(ok))


if __name__ == "__main__":
    ev = pick(*scan(ROOT / "csv/val-bbox.csv"), EVAL_CAP, skip=EXISTING)
    write(ev, "validation", ROOT / "eval")
    tr = pick(*scan(ROOT / "csv/train-bbox.csv"), TRAIN_CAP)
    write(tr, "train", ROOT / "train", val_every=10)
    for d in ("train", "eval"):
        val = "images/val" if d == "train" else "images/train"
        (ROOT / d / "data.yaml").write_text(f"path: {ROOT / d}\ntrain: images/train\nval: {val}\nnames: {NAMES}\n")
