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


def correct_subtype(analysis: Analysis, transcript: str) -> Analysis:
    """Use the keyword subtype when the LLM picked a different one whose own keywords were never said
    ("쿠팡입니다, 문 앞에 두고 갑니다" → LLM QUICK, keywords say PARCEL)."""
    entries = CATALOG.get(analysis.purpose).get("subtypes", [])
    said = _first_match(entries, transcript)
    if said is None or said == analysis.subtype:
        return analysis
    own = next((e for e in entries if e["id"] == analysis.subtype), {})
    if any(_said(w, transcript) for w in own.get("keywords", [])):
        return analysis
    return analysis.model_copy(update={"subtype": said})


def rule_analyze(transcript: str) -> Analysis:
    purpose = _first_match(CATALOG.purposes, transcript) or CATALOG.default
    subtype = _first_match(CATALOG.get(purpose).get("subtypes", []), transcript)
    return Analysis(
        summary=truncate_summary(transcript),
        purpose=purpose,
        subtype=normalize_subtype(purpose, subtype),
    )
