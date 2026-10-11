import json

from app.language.normalize import parse_llm_output
from app.language.purposes import CATALOG
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
    for purpose in CATALOG.ids:
        assert f"- {CATALOG.label(purpose)}:" in system["content"]
    assert "20자" in system["content"]
    assert messages[-1] == {"role": "user", "content": "택배 왔습니다"}


def test_few_shots_use_the_compact_answer_line():
    messages = build_messages("x")
    shots = [m for m in messages[1:-1] if m["role"] == "assistant"]
    assert len(shots) == len(CATALOG.few_shots)
    purposes = set()
    for shot, source in zip(shots, CATALOG.few_shots):
        subtype = CATALOG.label(source["purpose"], source["subtype"]) if source["subtype"] else "-"
        assert shot["content"] == f"{CATALOG.label(source['purpose'])}|{subtype}|{source['summary']}"
        parsed = parse_llm_output(shot["content"])
        assert (parsed.purpose, parsed.subtype, parsed.summary) == (
            source["purpose"], source["subtype"], source["summary"]
        )
        purposes.add(parsed.purpose)
    assert purposes == set(CATALOG.ids)


def test_system_prompt_asks_for_the_compact_line():
    assert "용건|세부 유형|요약" in build_messages("x")[0]["content"]


def test_analyze_uses_parsed_output():
    model = ScriptedQwen('{"summary": "택배 문 앞 보관", "purpose": "DELIVERY", "subtype": "PARCEL"}')
    assert model.analyze("택배 왔어요, 문 앞에 두고 가요") == Analysis(
        summary="택배 문 앞 보관", purpose="DELIVERY", subtype="PARCEL"
    )


def test_ungrounded_summary_is_replaced_by_transcript_but_purpose_kept():
    # "어 그게" → "근처 약국 문의" leaked from a few-shot example (review 2026-09-27).
    model = ScriptedQwen('{"summary": "근처 약국 문의", "purpose": "UNKNOWN"}')
    assert model.analyze("어 그게") == Analysis(summary="어 그게", purpose="UNKNOWN", flags=["SUMMARY_FROM_TRANSCRIPT"])


def test_grounded_summary_is_kept():
    model = ScriptedQwen('{"summary": "택배 문 앞 보관", "purpose": "DELIVERY", "subtype": "PARCEL"}')
    assert model.analyze("택배 왔어요, 문 앞에 둘게요") == Analysis(
        summary="택배 문 앞 보관", purpose="DELIVERY", subtype="PARCEL"
    )


def test_long_transcript_is_capped_for_the_llm():
    messages = build_messages("가" * 2000)
    assert len(messages[-1]["content"]) == 300


def test_analyze_falls_back_to_rules_on_garbage():
    model = ScriptedQwen("죄송하지만 이해하지 못했습니다")
    assert model.analyze("가스 검침 왔습니다") == Analysis(
        summary="가스 검침 왔습니다", purpose="SERVICE_VISIT", flags=["RULES_FALLBACK"]
    )
