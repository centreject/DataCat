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
    # Real models are wired in by later tasks (vision: Task 4, STT: Task 5, LLM: Task 7).
    return ModelRegistry(vision=None, stt=None, language=None, ready=True)
