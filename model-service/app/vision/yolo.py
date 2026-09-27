import os
import threading
from pathlib import Path

from PIL import Image

from app.config import DATA_DIR, Settings
from app.schemas import Detection

# Keep Ultralytics' settings file inside the project instead of ~/.config (must exist before import).
_CONFIG_DIR = DATA_DIR / "ultralytics"
_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_CONFIG_DIR))

from ultralytics import YOLO, YOLOE  # noqa: E402
from ultralytics.utils import SETTINGS  # noqa: E402
from ultralytics.utils.downloads import attempt_download_asset  # noqa: E402

PERSON_WEIGHTS = "yolo11s.pt"
PACKAGE_WEIGHTS = "yoloe-11s-seg.pt"
TEXT_ENCODER = "mobileclip_blt.ts"  # YOLOE's prompt encoder; fetched by bare name otherwise
COCO_PERSON = 0


class YoloVision:
    """COCO YOLO11 for people + open-vocabulary YOLOE for anything package-like."""

    def __init__(self, settings: Settings):
        weights = Path(settings.weights_dir)
        weights.mkdir(parents=True, exist_ok=True)
        # Ultralytics resolves bare asset names against SETTINGS["weights_dir"], else downloads to
        # the working directory. Pre-fetch the text encoder there so nothing lands in the cwd.
        SETTINGS.update({"weights_dir": str(weights)})
        attempt_download_asset(weights / TEXT_ENCODER)

        self.settings = settings
        self.person_model = YOLO(str(weights / PERSON_WEIGHTS))
        self.package_model = YOLOE(str(weights / PACKAGE_WEIGHTS))
        prompts = settings.package_prompts
        self.package_model.set_classes(prompts, self.package_model.get_text_pe(prompts))
        self.lock = threading.Lock()
        self.detect(Image.new("RGB", (640, 480)))  # warm-up so the first real request is fast

    def detect(self, image: Image.Image) -> list[Detection]:
        with self.lock:
            people = self.person_model.predict(
                image, classes=[COCO_PERSON], conf=self.settings.person_conf, half=True, verbose=False
            )[0]
            packages = self.package_model.predict(
                image, conf=self.settings.package_conf, half=True, verbose=False
            )[0]
        return [
            Detection(label="person", confidence=round(float(c), 4)) for c in people.boxes.conf
        ] + [
            Detection(label="package", confidence=round(float(c), 4)) for c in packages.boxes.conf
        ]
