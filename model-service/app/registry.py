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
    from app.language.qwen import QwenLanguage
    from app.speech.whisper import WhisperSpeech
    from app.vision.yolo import YoloVision

    return ModelRegistry(
        vision=YoloVision(settings),
        stt=WhisperSpeech(settings),
        language=QwenLanguage(settings),
        ready=True,
    )
