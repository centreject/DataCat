"""Keyword fallback, used only when the LLM fails or returns something unusable.

Keywords and their priority come from purposes.json (earlier purpose wins).
"""

import re

from app.language.normalize import normalize_subtype, truncate_summary
from app.language.purposes import CATALOG
from app.schemas import Analysis

NEGATION_WINDOW = 6  # "경찰 아니고요" — a keyword followed closely by 아니 is being denied


def _said(keyword: str, transcript: str) -> bool:
    """Keyword occurs, not as part of a longer number ("1192호" is not "119"), and not denied."""
    if keyword.isdigit():
        pattern = rf"(?<!\d){re.escape(keyword)}(?!\d)"
    else:
        pattern = re.escape(keyword)
    for m in re.finditer(pattern, transcript):
        if "아니" not in transcript[m.end() : m.end() + NEGATION_WINDOW]:
            return True
    return False


def _first_match(entries: list[dict], transcript: str) -> str | None:
    return next((e["id"] for e in entries if any(_said(w, transcript) for w in e.get("keywords", []))), None)


def rule_analyze(transcript: str) -> Analysis:
    purpose = _first_match(CATALOG.purposes, transcript) or CATALOG.default
    subtype = _first_match(CATALOG.get(purpose).get("subtypes", []), transcript)
    return Analysis(
        summary=truncate_summary(transcript),
        purpose=purpose,
        subtype=normalize_subtype(purpose, subtype),
    )
