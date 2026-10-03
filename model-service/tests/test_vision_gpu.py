"""Real-model checks. Run: pytest -m gpu tests/test_vision_gpu.py -v
Images come from `python eval/prepare_images.py` (+ team photos); missing folders skip."""

from pathlib import Path

import pytest
from PIL import Image

from app.config import Settings

pytestmark = pytest.mark.gpu

IMAGES = Path(__file__).resolve().parent.parent / "data" / "images"


@pytest.fixture(scope="module")
def vision(gpu_registry):
    return gpu_registry.vision


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


# Regression floors, set just under what the zero-shot setup measured on 2026-09-27
# (2026-10-04 prompts: person 93%, box 83%, bag 80%, empty FP 10%). They guard against regressions;
# they are NOT the plan's accuracy targets (person 95%, package 85%).
FLOORS = {"person": ("person", 0.90), "package_box": ("package", 0.75), "package_bag": ("package", 0.75)}


def hit_rate(vision, folder: str, label: str) -> float:
    files = sorted((IMAGES / folder).glob("*.jpg"))
    if not files:
        pytest.skip(f"no images in data/images/{folder}")
    hits = sum(any(d.label == label for d in vision.detect(Image.open(f).convert("RGB"))) for f in files)
    return hits / len(files)


@pytest.mark.parametrize("folder", sorted(FLOORS))
def test_folder_hit_rate_does_not_regress(vision, folder):
    label, floor = FLOORS[folder]
    assert hit_rate(vision, folder, label) >= floor


def test_empty_hallway_false_positive_rate(vision):
    assert hit_rate(vision, "empty", "package") <= 0.10
    assert hit_rate(vision, "empty", "person") <= 0.10


def test_animal_folder_is_detected_as_animal(vision):
    assert hit_rate(vision, "animal", "animal") >= 0.80
    assert hit_rate(vision, "animal", "person") <= 0.10


def test_real_hallway_images_are_not_low_visibility():
    from app.vision.quality import low_visibility

    files = sorted((IMAGES / "empty").glob("*.jpg"))
    if not files:
        pytest.skip("no images in data/images/empty")
    flagged = sum(low_visibility(Image.open(f).convert("RGB")) for f in files)
    assert flagged / len(files) <= 0.10


def test_loading_writes_nothing_to_working_directory(tmp_path, monkeypatch):
    from app.vision.yolo import YoloVision

    monkeypatch.chdir(tmp_path)
    YoloVision(Settings())
    assert list(tmp_path.iterdir()) == []


def test_load_registry_loads_vision(gpu_registry):
    from app.vision.yolo import YoloVision

    assert isinstance(gpu_registry.vision, YoloVision)
    assert gpu_registry.ready is True
