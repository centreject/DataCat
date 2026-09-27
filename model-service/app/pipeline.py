import logging

from app.language.rules import rule_analyze
from app.protocols import LanguageModel
from app.schemas import Analysis

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
