"""Real-model checks. Run: pytest -m gpu tests/test_qwen_gpu.py -v"""

import pytest

from app.config import Settings

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def qwen():
    from app.language.qwen import QwenLanguage

    return QwenLanguage(Settings())


def test_qwen_delivery(qwen):
    result = qwen.analyze("택배 왔습니다. 문 앞에 놓고 갈게요.")
    assert result.purpose == "DELIVERY"
    assert 0 < len(result.summary) <= 20


def test_qwen_inspection(qwen):
    assert qwen.analyze("관리사무소에서 소방 점검 나왔습니다").purpose == "INSPECTION"


def test_qwen_handles_negation_better_than_keywords(qwen):
    # Keyword rules would say DELIVERY because of "택배".
    assert qwen.analyze("택배 아니고요, 관리실에서 수도 점검 왔어요").purpose == "INSPECTION"


def test_qwen_visit(qwen):
    assert qwen.analyze("나 민수야, 근처 왔다가 들렀어. 전화 좀 줘").purpose == "VISIT"
