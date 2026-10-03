import json
import re

from app.language.purposes import CATALOG
from app.schemas import Analysis

PURPOSES = CATALOG.ids
SUMMARY_LIMIT = 20  # API v1.5 §7.3: max 20 characters including spaces
# Qwen occasionally mixes Chinese characters into Korean ("방문者 인사").
CJK_IDEOGRAPHS = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_WORD = re.compile(r"[가-힣A-Za-z0-9]+")
# Generic summary words that describe the visit rather than add facts; they need not be said.
GENERIC_WORDS = {
    "보관", "방문", "문의", "요청", "확인", "전달", "안내", "도착", "접수", "권유", "수거", "배송",
    "배달", "위협", "물품", "물건", "반납", "착오", "홍보", "예약", "알림",
}


def is_grounded(summary: str, transcript: str) -> bool:
    """True when every specific word of the summary was said (generic words like 보관·방문 excepted)
    and at least one specific word exists.

    Catches few-shot copies and inventions: "어 그게" → "근처 약국 문의", and "1192호 택배요" →
    "택배 문 앞 보관" (R3 review: "문 앞" was never said). A word also counts when its stem without
    the last syllable was said (맡김 ← 맡겨, 눌렀음 ← 눌렀어요).
    """
    spoken = re.sub(r"\s+", "", transcript)
    specific = [w for w in _WORD.findall(summary) if w not in GENERIC_WORDS]
    said = lambda w: w in spoken or (len(w) >= 2 and w[:-1] in spoken)  # noqa: E731
    return bool(specific) and all(said(w) for w in specific)


def truncate_summary(s: str, limit: int = SUMMARY_LIMIT) -> str:
    """Same rule as Spring's defensive cut: substring(0, limit-1) + "…"."""
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def normalize_subtype(purpose: str, subtype: object) -> str | None:
    """Subtype valid for the purpose, the purpose's default if it has subtypes, else None."""
    if not CATALOG.subtypes(purpose):
        return None
    return CATALOG.subtype_id(purpose, str(subtype or "")) or CATALOG.subtype_default(purpose)


def _fields(raw: str) -> dict | None:
    """Answer fields from the compact line `PURPOSE|SUBTYPE|summary`, or from JSON as a fallback."""
    for line in raw.strip().splitlines():
        if line.lstrip().startswith("{"):
            break  # JSON answer: its summary may contain "|"
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            subtype = None if parts[1] in ("", "-", "null", "None") else parts[1]
            return {"purpose": parts[0], "subtype": subtype, "summary": "|".join(parts[2:])}
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_llm_output(raw: str) -> Analysis | None:
    """Extract purpose, subtype and summary from LLM text; None when unusable."""
    data = _fields(raw)
    if data is None:
        return None
    summary = CJK_IDEOGRAPHS.sub("", str(data.get("summary") or ""))
    summary = truncate_summary(re.sub(r"\s{2,}", " ", summary))
    if not summary:
        return None
    purpose = CATALOG.purpose_id(str(data.get("purpose") or ""))
    if purpose is None:
        return None  # e.g. a subtype label in the purpose slot; the caller falls back to rules + flag
    return Analysis(summary=summary, purpose=purpose, subtype=normalize_subtype(purpose, data.get("subtype")))
