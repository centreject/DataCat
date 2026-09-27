import logging

from app.language.rules import rule_analyze
from app.media import decode_wav
from app.protocols import LanguageModel
from app.registry import ModelRegistry
from app.schemas import Analysis, AudioProcessResponse

log = logging.getLogger(__name__)


def analyze_transcript(model: LanguageModel, transcript: str) -> Analysis:
    # No speech: Spring/app decide what to show (agreed 2026-09-27), so return empty summary + ETC.
    if not transcript.strip():
        return Analysis(summary="", purpose="ETC")
    try:
        return model.analyze(transcript)
    except Exception:
        log.exception("language model failed; using keyword rules")
        return rule_analyze(transcript)


def process_audio(registry: ModelRegistry, wav: bytes) -> AudioProcessResponse:
    """STT → summary/purpose in one call (API v1.3 §7.4). Callers resolve models first."""
    transcript = registry.stt.transcribe(decode_wav(wav))
    analysis = analyze_transcript(registry.language, transcript)
    return AudioProcessResponse(transcript=transcript, purpose=analysis.purpose, summary=analysis.summary)
