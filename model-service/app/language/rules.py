"""Keyword fallback, used only when the LLM fails or returns something unusable."""

from app.language.normalize import truncate_summary
from app.schemas import Analysis

# Checked in this order; the first purpose with a matching keyword wins.
KEYWORDS = (
    ("DELIVERY", ("택배", "배달", "배송", "소포", "음식", "물건")),
    ("INSPECTION", ("검침", "점검", "관리사무소", "관리실", "가스", "소독", "수리", "설치", "공사")),
    ("VISIT", ("친구", "나야", "엄마", "아빠", "언니", "오빠", "형", "누나", "놀러")),
)


def rule_analyze(transcript: str) -> Analysis:
    purpose = next((p for p, words in KEYWORDS if any(w in transcript for w in words)), "ETC")
    return Analysis(summary=truncate_summary(transcript), purpose=purpose)
