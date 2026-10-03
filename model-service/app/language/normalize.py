import json
import re

from app.language.purposes import CATALOG
from app.schemas import Analysis

PURPOSES = CATALOG.ids
SUMMARY_LIMIT = 20  # API v1.4 §7.3: max 20 characters including spaces
# Qwen occasionally mixes Chinese characters into Korean ("방문者 인사").
CJK_IDEOGRAPHS = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_WORD = re.compile(r"[가-힣A-Za-z0-9]{2,}")


def is_grounded(summary: str, transcript: str) -> bool:
    """True when at least one word (2+ chars) of the summary occurs in what the visitor said.

    Catches summaries copied from few-shot examples or invented outright ("어 그게" → "근처 약국 문의").
    """
    spoken = re.sub(r"\s+", "", transcript)
    return any(word in spoken for word in _WORD.findall(summary))


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
    purpose = CATALOG.purpose_id(str(data.get("purpose") or "")) or CATALOG.default
    return Analysis(summary=summary, purpose=purpose, subtype=normalize_subtype(purpose, data.get("subtype")))
