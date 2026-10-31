"""Fine-tune YOLOE-11s on the Open Images package subset made by prep.py.

Usage (from model-service/):  python -u finetune/train.py full|probe EPOCHS DATA_ROOT
  full  = whole detector (used; best around epoch 5, overfits after — keep best.pt)
  probe = linear probing, only class-embedding layers train (tried; more empty-hallway false alarms)
Output: DATA_ROOT/runs/<mode>/weights/best.pt
"""

import os
import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[1]
W = SERVICE / "data" / "weights"
os.environ.setdefault("YOLO_CONFIG_DIR", str(SERVICE / "data" / "ultralytics"))
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

from ultralytics import YOLOE  # noqa: E402
from ultralytics.models.yolo.yoloe import YOLOEPETrainer  # noqa: E402
from ultralytics.utils import SETTINGS  # noqa: E402

SETTINGS.update({"weights_dir": str(W)})  # text encoder (mobileclip_blt.ts) is already there
mode, epochs, root = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
model = YOLOE("yoloe-11s.yaml").load(str(W / "yoloe-11s-seg.pt"))
freeze = None
if mode == "probe":
    head = len(model.model.model) - 1
    freeze = [str(i) for i in range(head)]
    freeze += [f"{head}.{n}" for n, _ in model.model.model[-1].named_children() if "cv3" not in n]
    freeze += [f"{head}.cv3.{a}.{b}" for a in range(3) for b in range(2)]
model.train(
    data=str(root / "train" / "data.yaml"), epochs=epochs, close_mosaic=min(5, epochs // 4),
    batch=16, imgsz=640, optimizer="AdamW", lr0=1e-3 if mode == "probe" else 2e-4, warmup_bias_lr=0.0,
    weight_decay=0.025, momentum=0.9, workers=4, device="0", trainer=YOLOEPETrainer, freeze=freeze,
    project=str(root / "runs"), name=mode, exist_ok=True, plots=False,
)
