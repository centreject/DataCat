import logging

from app.language.purposes import CATALOG
from app.language.rules import rule_analyze
from app.media import decode_wav
from app.protocols import LanguageModel
from app.registry import ModelRegistry
from app.schemas import Analysis, AudioProcessResponse

log = logging.getLogger(__name__)


def analyze_transcript(model: LanguageModel | None, transcript: str) -> Analysis:
    # No speech: Spring/app decide what to show (agreed 2026-09-27), so empty summary + default purpose.
    if not transcript.strip():
        return Analysis(summary="", purpose=CATALOG.default, flags=["NO_SPEECH"])
    if model is None:  # LLM failed to load
        return rule_analyze(transcript).model_copy(update={"flags": ["RULES_FALLBACK"]})
    try:
        return model.analyze(transcript)
    except Exception:
        log.exception("language model failed; using keyword rules")
        return rule_analyze(transcript).model_copy(update={"flags": ["RULES_FALLBACK"]})


def process_audio(registry: ModelRegistry, wav: bytes) -> AudioProcessResponse:
    """STT → summary/purpose in one call (API v1.4 §7.4). Callers resolve models first."""
    transcript = registry.stt.transcribe(decode_wav(wav))
    analysis = analyze_transcript(registry.language, transcript)
    return AudioProcessResponse(
        transcript=transcript,
        purpose=analysis.purpose,
        subtype=analysis.subtype,
        summary=analysis.summary,
        flags=analysis.flags,
    )
