"""Real-model checks. Run: pytest -m gpu tests/test_vision_gpu.py -v
Images come from `python eval/prepare_images.py` (+ team photos); missing folders skip."""

from pathlib import Path

import pytest
from PIL import Image

from app.config import Settings

pytestmark = pytest.mark.gpu

IMAGES = Path(__file__).resolve().parent.parent / "data" / "images"


@pytest.fixture(scope="module")
def vision():
    from app.vision.yolo import YoloVision

    return YoloVision(Settings())


def representative(folder: str) -> Image.Image:
    files = sorted((IMAGES / folder).glob("*.jpg"))
    if not files:
        pytest.skip(f"no images in data/images/{folder}")
    return Image.open(files[0]).convert("RGB")


def labels(vision, folder: str) -> set[str]:
    return {d.label for d in vision.detect(representative(folder))}


def test_person_detected(vision):
    assert "person" in labels(vision, "person")


@pytest.mark.parametrize("folder", ["package_box", "package_bag", "package_food", "package_cooler"])
def test_package_detected(vision, folder):
    assert "package" in labels(vision, folder)


def test_empty_hallway_has_no_detections(vision):
    assert vision.detect(representative("empty")) == []


def test_load_registry_loads_vision():
    from app.registry import load_registry
    from app.vision.yolo import YoloVision

    registry = load_registry(Settings())
    assert isinstance(registry.vision, YoloVision)
    assert registry.ready is True
