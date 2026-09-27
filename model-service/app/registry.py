from dataclasses import dataclass

from app.config import Settings
from app.protocols import LanguageModel, SpeechModel, VisionModel


@dataclass
class ModelRegistry:
    vision: VisionModel | None
    stt: SpeechModel | None
    language: LanguageModel | None
    ready: bool


def load_registry(settings: Settings) -> ModelRegistry:
    # Imported here so the app (and unit tests) start without GPU libraries loaded.
    from app.vision.yolo import YoloVision

    # STT and LLM are wired in by later tasks (STT: Task 5, LLM: Task 7).
    return ModelRegistry(vision=YoloVision(settings), stt=None, language=None, ready=True)
