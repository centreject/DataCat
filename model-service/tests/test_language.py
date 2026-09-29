import pytest

from app.language.normalize import is_grounded, parse_llm_output, truncate_summary
from app.language.rules import rule_analyze
from app.pipeline import analyze_transcript
from app.schemas import Analysis
from tests.conftest import ready_client

URL = "/internal/v1/language/analyze"


class FakeLanguage:
    def __init__(self, result=None, error: Exception | None = None):
        self.result, self.error, self.calls = result, error, 0

    def analyze(self, transcript: str) -> Analysis:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


# --- truncate_summary -------------------------------------------------------

def test_truncate_exact_20_kept():
    s = "가" * 20
    assert truncate_summary(s) == s


def test_truncate_21_becomes_19_plus_ellipsis():
    out = truncate_summary("가" * 21)
    assert len(out) == 20
    assert out == "가" * 19 + "…"


def test_truncate_strips_whitespace_first():
    assert truncate_summary("  택배 문 앞 보관  ") == "택배 문 앞 보관"


# --- parse_llm_output -------------------------------------------------------

def test_parse_valid():
    assert parse_llm_output('{"summary": "택배 문 앞 보관", "purpose": "DELIVERY", "subtype": "PARCEL"}') == Analysis(
        summary="택배 문 앞 보관", purpose="DELIVERY", subtype="PARCEL"
    )


def test_parse_with_surrounding_text():
    raw = '결과: {"summary": "가스 검침 방문", "purpose": "SERVICE_VISIT"} 입니다'
    assert parse_llm_output(raw) == Analysis(summary="가스 검침 방문", purpose="SERVICE_VISIT")


def test_parse_garbage_none():
    assert parse_llm_output("잘 모르겠습니다") is None
    assert parse_llm_output('{"summary": ') is None


def test_parse_empty_summary_none():
    assert parse_llm_output('{"summary": " ", "purpose": "PERSONAL_VISIT"}') is None


def test_parse_unknown_purpose_is_etc():
    assert parse_llm_output('{"summary": "음식 배달", "purpose": "FOOD"}').purpose == "UNKNOWN"


def test_parse_lowercase_purpose():
    assert parse_llm_output('{"summary": "택배", "purpose": "delivery"}').purpose == "DELIVERY"


def test_parse_long_summary_truncated():
    out = parse_llm_output('{"summary": "' + "가" * 30 + '", "purpose": "UNKNOWN"}')
    assert len(out.summary) == 20


def test_parse_strips_cjk_ideographs():
    # Qwen sometimes writes Chinese characters in Korean text ("방문者 인사", review 2026-09-27).
    assert parse_llm_output('{"summary": "방문者 인사", "purpose": "UNKNOWN"}').summary == "방문 인사"


def test_parse_summary_only_cjk_is_none():
    assert parse_llm_output('{"summary": "訪問者", "purpose": "UNKNOWN"}') is None


@pytest.mark.parametrize(
    "summary, transcript, grounded",
    [
        ("택배 문 앞 보관", "택배 왔습니다. 문 앞에 놓고 갈게요.", True),
        ("경비실 물품 맡김", "부재중이셔서 경비실에 맡겨 둘게요.", True),
        ("가스 검침 방문", "가스 검침하러 왔습니다.", True),
        ("근처 약국 문의", "어 그게", False),
        ("이웃 방문", "누나", False),
    ],
)
def test_is_grounded(summary, transcript, grounded):
    assert is_grounded(summary, transcript) is grounded


# --- rule_analyze -----------------------------------------------------------

@pytest.mark.parametrize(
    "transcript, purpose",
    [
        ("택배 문 앞에 두고 갑니다", "DELIVERY"),
        ("가스 검침 왔습니다", "SERVICE_VISIT"),
        ("엄마야 문 좀 열어줘", "PERSONAL_VISIT"),
        ("안녕하세요", "UNKNOWN"),
    ],
)
def test_rules_purpose(transcript, purpose):
    assert rule_analyze(transcript).purpose == purpose


# Held-out sentences (not in eval/purpose_cases.jsonl) for the expanded keyword list (M5).
@pytest.mark.parametrize(
    "transcript, purpose",
    [
        ("한진입니다, 박스 하나 경비실에 맡겼어요", "DELIVERY"),
        ("주문하신 꽃 가져왔습니다", "DELIVERY"),
        ("퀵서비스입니다", "DELIVERY"),
        ("한국전력에서 계량기 보러 왔어요", "SERVICE_VISIT"),
        ("윗집 누수 때문에 연락받고 왔어요", "SERVICE_VISIT"),
        ("정수기 필터 갈러 왔어요", "SERVICE_VISIT"),
        ("이모야, 문 열어 봐", "PERSONAL_VISIT"),
        ("할아버지 왔다", "PERSONAL_VISIT"),
        ("저 후배 지영이에요", "PERSONAL_VISIT"),
        ("교회에서 전도하러 왔어요", "SOLICITATION"),
        ("여론조사 기관에서 나왔습니다", "SOLICITATION"),
    ],
)
def test_rules_expanded_keywords(transcript, purpose):
    assert rule_analyze(transcript).purpose == purpose


def test_rules_summary_is_truncated_transcript():
    assert rule_analyze("가" * 30).summary == "가" * 19 + "…"


# --- analyze_transcript -----------------------------------------------------

def test_empty_transcript_skips_model():
    model = FakeLanguage(error=AssertionError("must not be called"))
    assert analyze_transcript(model, "  ") == Analysis(summary="", purpose="UNKNOWN")
    assert model.calls == 0


def test_model_exception_falls_back_to_rules():
    model = FakeLanguage(error=RuntimeError("CUDA OOM"))
    assert analyze_transcript(model, "택배 왔어요") == Analysis(summary="택배 왔어요", purpose="DELIVERY", subtype="PARCEL")


def test_model_result_is_used():
    model = FakeLanguage(result=Analysis(summary="친구 방문", purpose="PERSONAL_VISIT"))
    assert analyze_transcript(model, "나야 문 열어") == Analysis(summary="친구 방문", purpose="PERSONAL_VISIT")


# --- route ------------------------------------------------------------------

def test_analyze_route_contract():
    model = FakeLanguage(result=Analysis(summary="택배 문 앞 보관", purpose="DELIVERY", subtype="PARCEL"))
    with ready_client(language=model) as client:
        response = client.post(URL, json={"transcript": "택배 문 앞에 두고 갑니다"})
    assert response.status_code == 200
    assert response.json() == {"summary": "택배 문 앞 보관", "purpose": "DELIVERY", "subtype": "PARCEL"}


def test_analyze_route_uses_rules_when_llm_failed_to_load():
    with ready_client(language=None) as client:
        response = client.post(URL, json={"transcript": "택배 왔어요"})
    assert response.status_code == 200
    assert response.json() == {"summary": "택배 왔어요", "purpose": "DELIVERY", "subtype": "PARCEL"}


def test_analyze_route_empty_transcript():
    with ready_client(language=FakeLanguage(error=AssertionError())) as client:
        response = client.post(URL, json={"transcript": ""})
    assert response.json() == {"summary": "", "purpose": "UNKNOWN", "subtype": None}
