"""Purpose catalogue from 덕민님's classification plan (app/language/purposes.json)."""

import pydantic
import pytest

from app.language.normalize import parse_llm_output
from app.language.purposes import CATALOG
from app.language.rules import rule_analyze
from app.pipeline import analyze_transcript
from app.schemas import Analysis

PLAN_ORDER = [
    "PUBLIC_EMERGENCY", "SAFETY_REVIEW", "WRONG_VISIT", "PICKUP", "DELIVERY",
    "SERVICE_VISIT", "PERSONAL_VISIT", "SOLICITATION", "UNKNOWN",
]


def test_catalog_has_the_nine_plan_purposes_in_priority_order():
    assert CATALOG.ids == tuple(PLAN_ORDER)
    assert CATALOG.default == "UNKNOWN"


def test_only_delivery_has_subtypes():
    assert CATALOG.subtypes("DELIVERY") == ("FOOD", "MAIL", "GROCERY", "QUICK", "LARGE", "GIFT", "PARCEL", "OTHER")
    for purpose in PLAN_ORDER:
        if purpose != "DELIVERY":
            assert CATALOG.subtypes(purpose) == ()


def test_few_shots_follow_the_contract():
    shots = CATALOG.few_shots
    assert {s["purpose"] for s in shots} == set(PLAN_ORDER)
    for shot in shots:
        assert len(shot["summary"]) <= 20
        allowed = CATALOG.subtypes(shot["purpose"])
        assert shot["subtype"] in allowed if allowed else shot["subtype"] is None


# Keyword fallback follows the plan's priority and the delivery conflict rules.
@pytest.mark.parametrize(
    "transcript, purpose, subtype",
    [
        ("소방서입니다. 화재가 나서 대피하셔야 해요", "PUBLIC_EMERGENCY", None),
        ("문 안 열면 부숴버린다", "SAFETY_REVIEW", None),
        ("택배인데 주소를 잘못 찾았네요", "WRONG_VISIT", None),
        ("반품 상품 가지러 왔습니다", "PICKUP", None),
        ("쿠팡입니다. 문 앞에 두고 갑니다", "DELIVERY", "PARCEL"),
        ("쿠팡이츠 치킨 왔습니다", "DELIVERY", "FOOD"),
        ("등기 우편입니다. 서명 필요해요", "DELIVERY", "MAIL"),
        ("배달 왔습니다", "DELIVERY", "OTHER"),
        ("보일러 수리 기사입니다", "SERVICE_VISIT", None),
        ("엄마 나야", "PERSONAL_VISIT", None),
        ("교회에서 전도하러 왔어요", "SOLICITATION", None),
        ("안녕하세요", "UNKNOWN", None),
    ],
)
def test_rules_follow_plan_priority(transcript, purpose, subtype):
    result = rule_analyze(transcript)
    assert (result.purpose, result.subtype) == (purpose, subtype)


def test_parse_keeps_valid_delivery_subtype():
    parsed = parse_llm_output('{"summary": "치킨 도착", "purpose": "DELIVERY", "subtype": "FOOD"}')
    assert (parsed.purpose, parsed.subtype) == ("DELIVERY", "FOOD")


def test_parse_delivery_without_valid_subtype_is_other():
    assert parse_llm_output('{"summary": "배송", "purpose": "DELIVERY"}').subtype == "OTHER"
    assert parse_llm_output('{"summary": "배송", "purpose": "DELIVERY", "subtype": "DRONE"}').subtype == "OTHER"


def test_parse_drops_subtype_for_other_purposes():
    parsed = parse_llm_output('{"summary": "가스 검침", "purpose": "SERVICE_VISIT", "subtype": "FOOD"}')
    assert parsed.subtype is None


def test_parse_unknown_purpose_is_default():
    assert parse_llm_output('{"summary": "음식", "purpose": "ETC"}').purpose == "UNKNOWN"


def test_empty_transcript_is_unknown():
    class NeverCalled:
        def analyze(self, transcript):
            raise AssertionError

    assert analyze_transcript(NeverCalled(), " ") == Analysis(summary="", purpose="UNKNOWN", subtype=None)


def test_analysis_rejects_values_outside_the_catalog():
    with pytest.raises(pydantic.ValidationError):
        Analysis(summary="x", purpose="ETC")
    with pytest.raises(pydantic.ValidationError):
        Analysis(summary="x", purpose="SERVICE_VISIT", subtype="FOOD")
