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
        ("도를 아십니까? 잠깐 이야기 좀 나눠요", "SOLICITATION"),
        ("에어컨 설치 기사입니다. 두 시 예약이요", "SERVICE_VISIT"),
        ("물건은 관리실에 맡겨 놨어요", "DELIVERY"),
    ],
)
def test_qwen_strangers_and_services(qwen, transcript, purpose):
    assert qwen.analyze(transcript).purpose == purpose


@pytest.mark.parametrize(
    "transcript",
    ["택배 왔습니다. 문 앞에 놓고 갈게요.", "관리사무소에서 소방 점검 나왔습니다", "지금 몇 시예요?"],
)
def test_prefix_cache_gives_the_same_answer(qwen, transcript):
    from app.language.qwen import build_messages

    messages = build_messages(transcript)
    assert qwen.generate(messages) == qwen.generate(messages, use_prefix_cache=False)


def test_qwen_visit(qwen):
    assert qwen.analyze("나 민수야, 근처 왔다가 들렀어. 전화 좀 줘").purpose == "PERSONAL_VISIT"
