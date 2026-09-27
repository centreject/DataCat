"""YoloVision result mapping and predict arguments, with Ultralytics models stubbed (no GPU)."""

import threading
from types import SimpleNamespace

from PIL import Image

from app.config import Settings
from app.schemas import Detection
from app.vision.yolo import YoloVision


class StubModel:
    def __init__(self, confidences):
        self.confidences = confidences
        self.kwargs = None

    def predict(self, image, **kwargs):
        self.kwargs = kwargs
        return [SimpleNamespace(boxes=SimpleNamespace(conf=self.confidences))]


def stub_vision(people, packages) -> YoloVision:
    vision = object.__new__(YoloVision)  # skip __init__: no weights
    vision.settings = Settings()
    vision.person_model = StubModel(people)
    vision.package_model = StubModel(packages)
    vision.lock = threading.Lock()
    return vision


def test_ultralytics_never_pip_installs_at_runtime():
    # Ultralytics silently pip-installs missing requirements (it did for CLIP); in a container or at a
    # demo that means network access and unpinned versions. Dependencies come from requirements.txt.
    from ultralytics.utils import AUTOINSTALL

    assert AUTOINSTALL is False


def test_maps_both_models_to_labels_with_rounded_confidence():
    vision = stub_vision(people=[0.912345], packages=[0.5, 0.33333])
    assert vision.detect(Image.new("RGB", (4, 4))) == [
        Detection(label="person", confidence=0.9123),
        Detection(label="package", confidence=0.5),
        Detection(label="package", confidence=0.3333),
    ]


def test_person_model_only_looks_for_coco_person_at_person_threshold():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (4, 4)))
    assert vision.person_model.kwargs["classes"] == [0]
    assert vision.person_model.kwargs["conf"] == Settings().person_conf


def test_package_model_merges_overlapping_prompts():
    # "box" and "cardboard box" on one object must not become two packages (NMS across prompts).
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (4, 4)))
    assert vision.package_model.kwargs["agnostic_nms"] is True
    assert vision.package_model.kwargs["conf"] == Settings().package_conf


def test_uses_fp16_without_deprecated_half_flag():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (4, 4)))
    for model in (vision.person_model, vision.package_model):
        assert "half" not in model.kwargs
        assert model.kwargs["quantize"] == 16
