"""Status flags tell Spring how an answer was produced, so it can mark events for user review
(classification plan: '요약 실패 → 원문으로 분류하고 요약 실패 상태 추가', 'STT 실패 → 판단 불가')."""

from app.language.qwen import QwenLanguage
from app.pipeline import analyze_transcript
from app.schemas import Analysis
from tests.conftest import ready_client
from tests.fixtures.make_fixtures import tone_wav


class ScriptedQwen(QwenLanguage):
    def __init__(self, output: str):
        self.output = output

    def generate(self, messages, use_prefix_cache=True):
        return self.output


class Broken:
    def analyze(self, transcript):
        raise RuntimeError("CUDA out of memory")


def test_normal_llm_answer_has_no_flags():
    assert ScriptedQwen("배송|택배|택배 문 앞 보관").analyze("택배 왔어요, 문 앞에 둘게요").flags == []


def test_ungrounded_summary_is_flagged():
    result = ScriptedQwen("불명|-|근처 약국 문의").analyze("어 그게")
    assert result.summary == "어 그게"
    assert result.flags == ["SUMMARY_FROM_TRANSCRIPT"]


def test_unparseable_llm_answer_is_flagged_as_rules():
    assert ScriptedQwen("모르겠습니다").analyze("가스 검침 왔습니다").flags == ["RULES_FALLBACK"]


def test_no_speech_is_flagged():
    assert analyze_transcript(None, "  ").flags == ["NO_SPEECH"]


def test_missing_llm_is_flagged_as_rules():
    assert analyze_transcript(None, "택배 왔어요").flags == ["RULES_FALLBACK"]


def test_llm_exception_is_flagged_as_rules():
    assert analyze_transcript(Broken(), "택배 왔어요").flags == ["RULES_FALLBACK"]


def test_flags_reach_both_endpoints():
    class Speech:
        def transcribe(self, audio):
            return ""

    with ready_client(stt=Speech(), language=None) as client:
        audio = client.post("/internal/v1/audio/process", files={"audio": ("a.wav", tone_wav(1), "audio/wav")})
        text = client.post("/internal/v1/language/analyze", json={"transcript": "택배 왔어요"})
    assert audio.json()["flags"] == ["NO_SPEECH"]
    assert text.json()["flags"] == ["RULES_FALLBACK"]


def test_unknown_flag_is_rejected():
    import pydantic
    import pytest

    with pytest.raises(pydantic.ValidationError):
        Analysis(summary="x", purpose="UNKNOWN", flags=["SOMETHING"])
