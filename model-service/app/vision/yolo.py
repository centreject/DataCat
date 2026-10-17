import hashlib
import os
import threading
from pathlib import Path

import torch
from PIL import Image
from torchvision.ops import nms

from app.config import DATA_DIR, Settings
from app.schemas import Detection

# Keep Ultralytics' settings file inside the project instead of ~/.config (must exist before import).
_CONFIG_DIR = DATA_DIR / "ultralytics"
_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_CONFIG_DIR))
# Never pip-install missing packages at runtime (Ultralytics' default); they are pinned in requirements.txt.
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

from ultralytics import YOLO, YOLOE  # noqa: E402
from ultralytics.utils import SETTINGS  # noqa: E402
from ultralytics.utils.downloads import attempt_download_asset, safe_download  # noqa: E402

PERSON_WEIGHTS = "yolo11s.pt"
PACKAGE_WEIGHTS = "yoloe-11s-seg.pt"
# Fine-tuned on Open Images (finetune/, eval/README F1); Ultralytics only auto-fetches its own assets.
PACKAGE_FT_WEIGHTS = "yoloe-11s-package-oi.pt"
PACKAGE_FT_URL = f"https://github.com/centreject/DataCat/releases/download/package-model-v1/{PACKAGE_FT_WEIGHTS}"
TEXT_ENCODER = "mobileclip_blt.ts"  # YOLOE's prompt encoder; fetched by bare name otherwise
PACKAGE_FT_SHA256 = "0f0bf0ec859b7dc9297a8f8ee4d5e54c914b0f34715aa2bb1cef10060332c5ce"  # .pt is a pickle
MERGE_IOU = 0.7  # same object found by both package models counts once


def fetch_package_ft(path: Path) -> None:
    if not path.exists():
        safe_download(url=PACKAGE_FT_URL, file=path, min_bytes=1e5)
    if hashlib.sha256(path.read_bytes()).hexdigest() != PACKAGE_FT_SHA256:
        path.unlink()  # never load an unexpected pickle; the next start downloads it again
        raise RuntimeError(f"{path.name}: checksum mismatch")
COCO_PERSON = 0
# COCO bird, cat, dog → "animal" (plan: an animal alone is not a visitor).
COCO_ANIMALS = (14, 15, 16)


class YoloVision:
    """COCO YOLO11 for people + fine-tuned YOLOE and open-vocabulary YOLOE for packages."""

    def __init__(self, settings: Settings):
        weights = Path(settings.weights_dir)
        weights.mkdir(parents=True, exist_ok=True)
        # Ultralytics resolves bare asset names against SETTINGS["weights_dir"], else downloads to
        # the working directory. Pre-fetch the text encoder there so nothing lands in the cwd.
        SETTINGS.update({"weights_dir": str(weights)})
        attempt_download_asset(weights / TEXT_ENCODER)
        fetch_package_ft(weights / PACKAGE_FT_WEIGHTS)

        self.settings = settings
        self.person_model = YOLO(str(weights / PERSON_WEIGHTS))
        self.package_model = YOLOE(str(weights / PACKAGE_WEIGHTS))
        prompts = settings.package_prompts
        self.package_model.set_classes(prompts, self.package_model.get_text_pe(prompts))
        self.package_ft_model = YOLOE(str(weights / PACKAGE_FT_WEIGHTS))
        self.lock = threading.Lock()
        self.detect(Image.new("RGB", (640, 480)))  # warm-up so the first real request is fast

    def detect(self, image: Image.Image) -> list[Detection]:
        with self.lock:
            people = self.person_model.predict(
                image,
                classes=[COCO_PERSON, *COCO_ANIMALS],
                conf=self.settings.person_conf,
                quantize=16,
                verbose=False,
            )[0]
            # agnostic_nms: overlapping prompts ("box", "cardboard box") on one object count once.
            packages = [
                model.predict(image, conf=conf, agnostic_nms=True, quantize=16, verbose=False)[0].boxes
                for model, conf in (
                    (self.package_ft_model, self.settings.package_ft_conf),
                    (self.package_model, self.settings.package_conf),
                )
            ]
        xyxy = torch.cat([b.xyxy.float().cpu() for b in packages])
        conf = torch.cat([b.conf.float().cpu() for b in packages])
        return [
            Detection(label="person" if int(k) == COCO_PERSON else "animal", confidence=round(float(c), 4))
            for c, k in zip(people.boxes.conf, people.boxes.cls)
        ] + [
            Detection(label="package", confidence=round(float(conf[i]), 4)) for i in nms(xyxy, conf, MERGE_IOU)
        ]
