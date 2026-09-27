import json

from app.language.qwen import QwenLanguage, build_messages
from app.schemas import Analysis


class ScriptedQwen(QwenLanguage):
    """QwenLanguage with generation replaced by a fixed string (no weights loaded)."""

    def __init__(self, output: str):
        self.output = output

    def generate(self, messages: list[dict]) -> str:
        return self.output


def test_build_messages_contains_all_purposes():
    messages = build_messages("택배 왔습니다")
    system = messages[0]
    assert system["role"] == "system"
    for purpose in ("DELIVERY", "INSPECTION", "VISIT", "ETC"):
        assert purpose in system["content"]
    assert "20자" in system["content"]
    assert messages[-1] == {"role": "user", "content": "택배 왔습니다"}


def test_build_messages_few_shots_are_valid_short_json():
    messages = build_messages("x")
    shots = [m for m in messages[1:-1] if m["role"] == "assistant"]
    assert len(shots) == 4
    purposes = set()
    for shot in shots:
        data = json.loads(shot["content"])
        assert set(data) == {"summary", "purpose"}
        assert len(data["summary"]) <= 20
        purposes.add(data["purpose"])
    assert purposes == {"DELIVERY", "INSPECTION", "VISIT", "ETC"}


def test_analyze_uses_parsed_output():
    model = ScriptedQwen('{"summary": "택배 문 앞 보관", "purpose": "DELIVERY"}')
    assert model.analyze("택배 두고 가요") == Analysis(summary="택배 문 앞 보관", purpose="DELIVERY")


def test_analyze_falls_back_to_rules_on_garbage():
    model = ScriptedQwen("죄송하지만 이해하지 못했습니다")
    assert model.analyze("가스 검침 왔습니다") == Analysis(summary="가스 검침 왔습니다", purpose="INSPECTION")
