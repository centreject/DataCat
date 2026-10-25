import hashlib
import logging
import os
from pathlib import Path

import torch
from PIL import Image
from torchvision.ops import nms

from app.config import DATA_DIR, Settings
from app.gpu import GpuSlot
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
# .pt files are pickles (loading one runs code), so every weight file must match what we tested.
SHA256 = {
    PERSON_WEIGHTS: "85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5",
    PACKAGE_WEIGHTS: "8e439445c87338b79d9ce21dec109f4621e26df67e94d26ea1a98c1e64dce3e3",
    TEXT_ENCODER: "a67804d1b0f07b8b9a20c1761ec0847f34660f5fa338ec70e8f3fce68ed95e54",
    PACKAGE_FT_WEIGHTS: "0f0bf0ec859b7dc9297a8f8ee4d5e54c914b0f34715aa2bb1cef10060332c5ce",
}
MERGE_IOU = 0.7  # same object found by both package models counts once

log = logging.getLogger(__name__)


def fetch_verified(path: Path, url: str | None = None) -> None:
    """Download if missing (Ultralytics' release, or `url`), then refuse anything but the tested file."""
    if not path.exists():
        if url:
            safe_download(url=url, file=path, min_bytes=1e5)
        else:
            attempt_download_asset(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256[path.name]:
        path.unlink()  # never load an unexpected pickle; the next start downloads it again
        raise RuntimeError(f"{path.name}: checksum mismatch")


def fetch_package_ft(path: Path) -> None:
    fetch_verified(path, PACKAGE_FT_URL)


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
        for name in (TEXT_ENCODER, PERSON_WEIGHTS, PACKAGE_WEIGHTS):
            fetch_verified(weights / name)
        try:
            fetch_package_ft(weights / PACKAGE_FT_WEIGHTS)
            self.package_ft_model = YOLOE(str(weights / PACKAGE_FT_WEIGHTS))
            prompts, self.package_mode = settings.package_prompts, "fine-tuned"
        except Exception:
            # Packages are an extra; losing them must not take person detection down with them.
            log.exception("fine-tuned package weights unavailable; zero-shot prompts only")
            self.package_ft_model = None
            prompts, self.package_mode = settings.package_fallback_prompts, "zero-shot"

        self.settings = settings
        self.person_model = YOLO(str(weights / PERSON_WEIGHTS))
        self.package_model = YOLOE(str(weights / PACKAGE_WEIGHTS))
        self.package_model.set_classes(prompts, self.package_model.get_text_pe(prompts))
        self.slot = GpuSlot("vision", settings.vision_wait_s)
        self.version = f"yolo11s + yoloe-11s ({self.package_mode})"
        self.detect(Image.new("RGB", (640, 480)))  # warm-up so the first real request is fast

    def detect(self, image: Image.Image) -> list[Detection]:
        package_models = [(self.package_model, self.settings.package_conf)]
        if self.package_ft_model is not None:
            package_models.insert(0, (self.package_ft_model, self.settings.package_ft_conf))
        with self.slot():
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
                for model, conf in package_models
            ]
        xyxy = torch.cat([b.xyxy.float().cpu() for b in packages])
        conf = torch.cat([b.conf.float().cpu() for b in packages])
        return [
            Detection(label="person" if int(k) == COCO_PERSON else "animal", confidence=round(float(c), 4))
            for c, k in zip(people.boxes.conf, people.boxes.cls)
        ] + [
            Detection(label="package", confidence=round(float(conf[i]), 4)) for i in nms(xyxy, conf, MERGE_IOU)
        ]
