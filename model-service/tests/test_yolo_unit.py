"""YoloVision result mapping and predict arguments, with Ultralytics models stubbed (no GPU)."""

from types import SimpleNamespace

import pytest
import torch
from PIL import Image

from app.config import Settings
from app.schemas import Detection
from app.gpu import GpuSlot
from app.vision import yolo
from app.vision.yolo import YoloVision


class StubModel:
    def __init__(self, confidences, classes=None, boxes=None):
        self.confidences = confidences
        self.classes = classes if classes is not None else [0] * len(confidences)
        # default: one separate 10x10 box per detection, so nothing overlaps
        self.boxes = boxes if boxes is not None else [[20 * i, 0, 20 * i + 10, 10] for i in range(len(confidences))]
        self.kwargs = None

    def predict(self, image, **kwargs):
        self.kwargs = kwargs
        boxes = SimpleNamespace(conf=torch.tensor(self.confidences, dtype=torch.float32), cls=self.classes,
                                xyxy=torch.tensor(self.boxes, dtype=torch.float32).reshape(-1, 4))
        return [SimpleNamespace(boxes=boxes)]


def stub_vision(people, packages, packages_ft=()) -> YoloVision:
    vision = object.__new__(YoloVision)  # skip __init__: no weights
    vision.settings = Settings()
    vision.person_model = StubModel(people)
    vision.package_model = StubModel(packages)
    vision.package_ft_model = StubModel(list(packages_ft))
    vision.slot = GpuSlot("vision", 1)
    return vision


def test_ultralytics_never_pip_installs_at_runtime():
    # Ultralytics silently pip-installs missing requirements (it did for CLIP); in a container or at a
    # demo that means network access and unpinned versions. Dependencies come from requirements.txt.
    from ultralytics.utils import AUTOINSTALL

    assert AUTOINSTALL is False


def test_coco_animals_become_animal_label():
    # Plan: "동물만 감지되면 사람 방문으로 응대하지 않는다" — Spring needs to tell animals from people.
    vision = stub_vision(people=[0.9, 0.8, 0.7], packages=[])
    vision.person_model.classes = [0, 16, 15]  # person, dog, cat
    assert [d.label for d in vision.detect(Image.new("RGB", (200, 200)))] == ["person", "animal", "animal"]


def test_person_model_also_looks_for_birds_cats_dogs():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (200, 200)))
    assert vision.person_model.kwargs["classes"] == [0, 14, 15, 16]


def test_maps_both_models_to_labels_with_rounded_confidence():
    vision = stub_vision(people=[0.912345], packages=[0.5, 0.33333])
    assert vision.detect(Image.new("RGB", (200, 200))) == [
        Detection(label="person", confidence=0.9123),
        Detection(label="package", confidence=0.5),
        Detection(label="package", confidence=0.3333),
    ]


def test_package_found_by_both_models_counts_once():
    vision = stub_vision([], packages=[0.3], packages_ft=[0.8])  # both default to the same box
    assert vision.detect(Image.new("RGB", (200, 200))) == [Detection(label="package", confidence=0.8)]


def test_packages_from_either_model_are_kept():
    vision = stub_vision([], packages=[0.3], packages_ft=[0.8])
    vision.package_model.boxes = [[100, 100, 120, 120]]  # e.g. a flower bouquet elsewhere in the frame
    assert [d.confidence for d in vision.detect(Image.new("RGB", (200, 200)))] == [0.8, 0.3]


def test_fine_tuned_model_uses_its_own_threshold():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (200, 200)))
    assert vision.package_ft_model.kwargs["conf"] == Settings().package_ft_conf


def test_fine_tuned_weights_with_wrong_checksum_are_deleted(tmp_path):
    bad = tmp_path / yolo.PACKAGE_FT_WEIGHTS
    bad.write_bytes(b"not the released file")
    with pytest.raises(RuntimeError, match="checksum"):
        yolo.fetch_package_ft(bad)
    assert not bad.exists()


def test_person_model_uses_person_threshold():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (200, 200)))
    assert vision.person_model.kwargs["conf"] == Settings().person_conf


def test_package_model_merges_overlapping_prompts():
    # "box" and "cardboard box" on one object must not become two packages (NMS across prompts).
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (200, 200)))
    assert vision.package_model.kwargs["agnostic_nms"] is True
    assert vision.package_model.kwargs["conf"] == Settings().package_conf


def test_uses_fp16_without_deprecated_half_flag():
    vision = stub_vision([], [])
    vision.detect(Image.new("RGB", (200, 200)))
    for model in (vision.person_model, vision.package_model, vision.package_ft_model):
        assert "half" not in model.kwargs
        assert model.kwargs["quantize"] == 16



def test_without_fine_tuned_weights_zero_shot_still_finds_packages():
    # Fine-tuned weights missing (offline first start): vision keeps working with prompts only.
    vision = stub_vision([], packages=[0.6])
    vision.package_ft_model = None
    assert vision.detect(Image.new("RGB", (200, 200))) == [Detection(label="package", confidence=0.6)]
