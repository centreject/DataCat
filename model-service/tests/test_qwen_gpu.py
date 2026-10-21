"""Real-model checks. Run: pytest -m gpu tests/test_qwen_gpu.py -v"""

import pytest

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def qwen(gpu_registry):
    return gpu_registry.language


def test_load_registry_loads_language(gpu_registry):
    from app.language.qwen import QwenLanguage

    assert isinstance(gpu_registry.language, QwenLanguage)


def test_qwen_delivery(qwen):
    result = qwen.analyze("택배 왔습니다. 문 앞에 놓고 갈게요.")
    assert result.purpose == "DELIVERY"
    assert 0 < len(result.summary) <= 20


def test_qwen_inspection(qwen):
    assert qwen.analyze("관리사무소에서 소방 점검 나왔습니다").purpose == "SERVICE_VISIT"


def test_qwen_handles_negation_better_than_keywords(qwen):
    # Keyword rules would say DELIVERY because of "택배".
    assert qwen.analyze("택배 아니고요, 관리실에서 수도 점검 왔어요").purpose == "SERVICE_VISIT"


# Held-out sentences (not in eval/purpose_cases.jsonl) for the categories the first eval confused.
@pytest.mark.parametrize(
    "transcript, purpose",
    [
        ("보험 상품 안내드리러 왔습니다", "SOLICITATION"),
        pytest.param(
            "도를 아십니까? 잠깐 이야기 좀 나눠요", "SOLICITATION",
            # Known miss since the compact Korean-label format (2026-10-04): the idiom is read as
            # small talk. Not patched into the prompt, which would only fit this one sentence.
            marks=pytest.mark.xfail(reason="idiom for religious solicitation not recognised", strict=False),
        ),
        ("에어컨 설치 기사입니다. 두 시 예약이요", "SERVICE_VISIT"),
        ("물건은 관리실에 맡겨 놨어요", "DELIVERY"),
    ],
)
def test_qwen_strangers_and_services(qwen, transcript, purpose):
    assert qwen.analyze(transcript).purpose == purpose


# Held-out sentences (not in eval/purpose_cases.jsonl) for the rules added on 2026-10-04 after the
# 100-case eval: danger outranks inspection, public offices are emergencies, returning a borrowed
# item is a personal visit, and delivery subtypes follow the item named.
@pytest.mark.parametrize(
    "transcript, purpose, subtype",
    [
        ("도시가스 누출 신고 받고 왔습니다", "PUBLIC_EMERGENCY", None),
        ("구청에서 나왔습니다. 확인할 서류가 있어서요", "PUBLIC_EMERGENCY", None),
        ("저 영수예요, 지난번 빌려 간 우산 돌려주러 왔어요", "PERSONAL_VISIT", None),
        ("소파 배송입니다. 두 명이서 들고 올라왔어요", "DELIVERY", "LARGE"),
        ("커피 배달 왔습니다", "DELIVERY", "FOOD"),
    ],
)
def test_qwen_plan_rules_on_held_out_sentences(qwen, transcript, purpose, subtype):
    result = qwen.analyze(transcript)
    assert (result.purpose, result.subtype) == (purpose, subtype)


@pytest.mark.parametrize(
    "transcript",
    ["택배 왔습니다. 문 앞에 놓고 갈게요.", "관리사무소에서 소방 점검 나왔습니다", "지금 몇 시예요?"],
)
def test_prefix_cache_gives_the_same_answer(qwen, transcript):
    from app.language.qwen import build_messages

    from app.language.normalize import parse_llm_output

    # Compare the decision, not the exact wording: 4-bit kernels can drift by a word between
    # input lengths (R3 review saw "문의 내용 없음" vs "문의 없음").
    messages = build_messages(transcript)
    cached = parse_llm_output(qwen.generate(messages))
    uncached = parse_llm_output(qwen.generate(messages, use_prefix_cache=False))
    assert (cached.purpose, cached.subtype) == (uncached.purpose, uncached.subtype)


def test_summary_does_not_invent_a_place(qwen):
    # R3: "법원 등기 우편 왔습니다" was summarised as "...문 앞 보관" — never said.
    assert "문 앞" not in qwen.analyze("법원 등기 우편 왔습니다").summary


def test_qwen_visit(qwen):
    assert qwen.analyze("나 민수야, 근처 왔다가 들렀어. 전화 좀 줘").purpose == "PERSONAL_VISIT"
