import logging
from dataclasses import dataclass

from app.config import Settings
from app.protocols import LanguageModel, SpeechModel, VisionModel

log = logging.getLogger(__name__)


@dataclass
class ModelRegistry:
    vision: VisionModel | None
    stt: SpeechModel | None
    language: LanguageModel | None
    ready: bool
    failed: tuple[str, ...] = ()  # models that raised while loading (e.g. CUDA OOM)


def load_registry(settings: Settings) -> ModelRegistry:
    # Imported here so the app (and unit tests) start without GPU libraries loaded.
    import app.language.qwen
    import app.speech.whisper
    import app.vision.yolo

    factories = {
        "vision": lambda: app.vision.yolo.YoloVision(settings),
        "stt": lambda: app.speech.whisper.WhisperSpeech(settings),
        "language": lambda: app.language.qwen.QwenLanguage(settings),
    }
    # Each model loads on its own: an LLM out-of-memory must not also take down person detection.
    models, failed = {}, []
    for name, build in factories.items():
        try:
            models[name] = build()
        except Exception:
            log.exception("failed to load %s model", name)
            models[name] = None
            failed.append(name)
    return ModelRegistry(**models, ready=True, failed=tuple(failed))
