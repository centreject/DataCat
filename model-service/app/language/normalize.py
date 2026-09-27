import json
from typing import get_args

from app.schemas import Analysis, Purpose

PURPOSES = get_args(Purpose)
SUMMARY_LIMIT = 20  # API v1.3 §7.3: max 20 characters including spaces


def truncate_summary(s: str, limit: int = SUMMARY_LIMIT) -> str:
    """Same rule as Spring's defensive cut: substring(0, limit-1) + "…"."""
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def parse_llm_output(raw: str) -> Analysis | None:
    """Extract {"summary", "purpose"} from LLM text; None when unusable."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    summary = truncate_summary(str(data.get("summary") or ""))
    if not summary:
        return None
    purpose = str(data.get("purpose") or "").strip().upper()
    return Analysis(summary=summary, purpose=purpose if purpose in PURPOSES else "ETC")
