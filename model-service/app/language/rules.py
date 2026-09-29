"""Keyword fallback, used only when the LLM fails or returns something unusable.

Keywords and their priority come from purposes.json (earlier purpose wins).
"""

from app.language.normalize import normalize_subtype, truncate_summary
from app.language.purposes import CATALOG
from app.schemas import Analysis


def _first_match(entries: list[dict], transcript: str) -> str | None:
    return next((e["id"] for e in entries if any(w in transcript for w in e.get("keywords", []))), None)


def rule_analyze(transcript: str) -> Analysis:
    purpose = _first_match(CATALOG.purposes, transcript) or CATALOG.default
    subtype = _first_match(CATALOG.get(purpose).get("subtypes", []), transcript)
    return Analysis(
        summary=truncate_summary(transcript),
        purpose=purpose,
        subtype=normalize_subtype(purpose, subtype),
    )
