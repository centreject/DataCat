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
    allowed = CATALOG.subtypes(purpose)
    if not allowed:
        return None
    value = str(subtype or "").strip().upper()
    return value if value in allowed else CATALOG.subtype_default(purpose)


def parse_llm_output(raw: str) -> Analysis | None:
    """Extract {"summary", "purpose", "subtype"} from LLM text; None when unusable."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    summary = CJK_IDEOGRAPHS.sub("", str(data.get("summary") or ""))
    summary = truncate_summary(re.sub(r"\s{2,}", " ", summary))
    if not summary:
        return None
    purpose = str(data.get("purpose") or "").strip().upper()
    if purpose not in PURPOSES:
        purpose = CATALOG.default
    return Analysis(summary=summary, purpose=purpose, subtype=normalize_subtype(purpose, data.get("subtype")))
