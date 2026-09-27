"""Keyword fallback, used only when the LLM fails or returns something unusable."""

from app.language.normalize import truncate_summary
from app.schemas import Analysis

# Checked in this order; the first purpose with a matching keyword wins.
KEYWORDS = (
    ("DELIVERY", (
        "택배", "배달", "배송", "소포", "음식", "물건", "우편", "등기", "우체국", "주문", "퀵",
        "박스", "보냉백", "경비실", "쿠팡", "대한통운", "한진", "로젠", "치킨", "피자",
    )),
    ("INSPECTION", (
        "검침", "점검", "관리사무소", "관리실", "가스", "소독", "방역", "수리", "설치", "공사",
        "계량기", "한전", "한국전력", "누수", "보일러", "필터", "기사",
    )),
    ("VISIT", (
        "친구", "나야", "엄마", "아빠", "언니", "오빠", "형", "누나", "동생", "놀러",
        "할머니", "할아버지", "이모", "삼촌", "고모", "아들", "딸", "선배", "후배",
    )),
)


def rule_analyze(transcript: str) -> Analysis:
    purpose = next((p for p, words in KEYWORDS if any(w in transcript for w in words)), "ETC")
    return Analysis(summary=truncate_summary(transcript), purpose=purpose)
