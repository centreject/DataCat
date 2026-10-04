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
    # 2026-10-04: noun endings the prompt asks for ("설문조사 진행", "엘리베이터 위치 문의").
    "진행", "위치", "예정",
}


_HANGUL_BASE, _JONG_COUNT, _MIEUM = 0xAC00, 28, 16
_PREDICATE_ENDINGS = ("하기", "세요", "기", "음", "다", "요")
# Contracted vowels: 주어→줘, 놓아→놨, 두어→둬 (medial indices: ㅗ→ㅘ, ㅜ→ㅝ, ㅣ→ㅕ, ㅡ→ㅓ).
_VOWEL_CONTRACTIONS = {8: 9, 13: 14, 20: 6, 18: 4}


def _any_final(ch: str) -> str:
    """Regex class: the syllable with any final consonant, also in its contracted-vowel form."""
    code = ord(ch) - _HANGUL_BASE
    if not 0 <= code < 11172:
        return re.escape(ch)
    initial, medial = divmod(code // _JONG_COUNT, 21)
    bases = [medial] + ([_VOWEL_CONTRACTIONS[medial]] if medial in _VOWEL_CONTRACTIONS else [])
    starts = [_HANGUL_BASE + (initial * 21 + m) * _JONG_COUNT for m in bases]
    return "[" + "".join(f"{chr(s)}-{chr(s + _JONG_COUNT - 1)}" for s in starts) + "]"


def _predicate_said(word: str, spoken: str) -> bool:
    """The summary's closing predicate was said in another inflection: 둠←둘게요, 놓음←놨어요,
    주기←줘, 간다←갈게요. Only the stem is compared, its last syllable ignoring the final consonant."""
    stem = next((word[: -len(e)] for e in _PREDICATE_ENDINGS if word.endswith(e) and len(word) > len(e)), None)
    if stem is None:
        code = ord(word[-1]) - _HANGUL_BASE
        if not (0 <= code < 11172 and code % _JONG_COUNT == _MIEUM):
            return False
        stem = word[:-1] + chr(ord(word[-1]) - _MIEUM)  # nominal -ㅁ: 둠 → 두
    return re.search(re.escape(stem[:-1]) + _any_final(stem[-1]), spoken) is not None


def is_grounded(summary: str, transcript: str) -> bool:
    """True when every specific word of the summary was said (generic words like 보관·방문 excepted)
    and at least one specific word exists.

    Catches few-shot copies and inventions: "어 그게" → "근처 약국 문의", and "1192호 택배요" →
    "택배 문 앞 보관" (R3 review: "문 앞" was never said). A word also counts when its stem without
    the last syllable was said (맡김 ← 맡겨, 눌렀음 ← 눌렀어요). The last word, where a noun-style
    summary puts its predicate, may differ in inflection (_predicate_said); places and objects come
    earlier and must match as said.
    """
    spoken = re.sub(r"\s+", "", transcript)
    words = _WORD.findall(summary)
    specific = [(i, w) for i, w in enumerate(words) if w not in GENERIC_WORDS]

    def said(i: int, w: str) -> bool:
        if w in spoken or (len(w) >= 2 and w[:-1] in spoken):
            return True
        return i == len(words) - 1 and _predicate_said(w, spoken)

    return bool(specific) and all(said(i, w) for i, w in specific)


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
