"""Regression tests for the R3 review findings (2026-10-04)."""

import io

import pytest
from PIL import Image

from app.language.normalize import is_grounded, parse_llm_output
from app.language.purposes import CATALOG
from app.language.qwen import QwenLanguage
from app.language.rules import rule_analyze
from app.schemas import Detection
from app.vision.quality import low_visibility
from tests.conftest import ready_client


class ScriptedQwen(QwenLanguage):
    def __init__(self, output: str):
        self.output = output

    def generate(self, messages, use_prefix_cache=True):
        return self.output


# R3 #1: an unknown purpose label must not silently become UNKNOWN.
@pytest.mark.parametrize("answer", ["택배|-|택배 왔음", "배달|음식|치킨 배달"])
def test_unknown_purpose_label_falls_back_to_rules_with_flag(answer):
    result = ScriptedQwen(answer).analyze("택배 왔어요")
    assert (result.purpose, result.flags) == ("DELIVERY", ["RULES_FALLBACK"])


def test_parse_returns_none_for_unknown_purpose_label():
    assert parse_llm_output("택배|-|택배 왔음") is None


# R3 #3: keyword fallback must not raise false emergencies.
@pytest.mark.parametrize(
    "transcript, purpose",
    [
        ("1192호 택배요", "DELIVERY"),
        ("경찰 아니고요 택배입니다", "DELIVERY"),
        ("응급 상황 아니고요, 그냥 물건 놓고 갈게요", "DELIVERY"),
        ("소방 시설 점검 나왔습니다", "SERVICE_VISIT"),
        ("법원 등기 우편 왔습니다", "DELIVERY"),
        ("누구 계세요? 보험 상품 소개드리려고요", "SOLICITATION"),
        ("119 구급대입니다", "PUBLIC_EMERGENCY"),
        ("불이 났어요, 대피하세요", "PUBLIC_EMERGENCY"),
    ],
)
def test_rules_avoid_false_emergencies(transcript, purpose):
    assert rule_analyze(transcript).purpose == purpose


# R3 #4: priority follows the plan (수거 before 착오), keeping the delivery conflict rule (착오 before 배송).
def test_priority_order_follows_plan_with_documented_exception():
    assert CATALOG.ids == (
        "PUBLIC_EMERGENCY", "SAFETY_REVIEW", "PICKUP", "WRONG_VISIT", "DELIVERY",
        "SERVICE_VISIT", "PERSONAL_VISIT", "SOLICITATION", "UNKNOWN",
    )


def test_returning_a_misdelivered_parcel_is_pickup():
    assert rule_analyze("아까 잘못 배송된 택배 다시 가져가겠습니다").purpose == "PICKUP"


# R3 #2: a dark frame in which a person is detected is not "low visibility".
def test_dark_but_textured_image_is_not_low_visibility():
    import numpy as np

    # Dark (mean 18) but textured (std 18): 8-px checkerboard of 0 and 36, like a dim hallway at night.
    board = (np.indices((48, 64)) // 8).sum(axis=0) % 2 * 36
    assert not low_visibility(Image.fromarray(board.astype(np.uint8)).convert("RGB"))


def test_route_skips_low_visibility_when_a_person_is_detected():
    class SeesPerson:
        def detect(self, image):
            return [Detection(label="person", confidence=0.9)]

    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (3, 3, 3)).save(buf, format="JPEG")
    with ready_client(vision=SeesPerson()) as client:
        response = client.post("/internal/v1/vision/detect", files={"image": ("x.jpg", buf.getvalue(), "image/jpeg")})
    assert response.json()["flags"] == []


# R3 #5: summaries may not add words the visitor did not say ("문 앞 보관" template).
@pytest.mark.parametrize(
    "summary, transcript, grounded",
    [
        ("택배 문 앞 보관", "1192호 택배요", False),
        ("법원 등기 우편 문 앞 보관", "법원 등기 우편 왔습니다", False),
        ("딸기 문 앞 보관", "딸기 한 박스 배달 왔어요", False),
        ("택배 문 앞 보관", "택배 왔습니다. 문 앞에 두고 갈게요", True),
        ("가스 검침 방문", "가스 검침하러 왔습니다", True),
        ("경비실 물품 맡김", "부재중이셔서 경비실에 맡겨 둘게요", True),
    ],
)
def test_grounding_requires_every_specific_word(summary, transcript, grounded):
    assert is_grounded(summary, transcript) is grounded


# R3 minor: a JSON answer whose summary contains "|" is still read as JSON.
def test_json_answer_with_pipe_in_summary():
    parsed = parse_llm_output('{"purpose": "배송", "subtype": "택배", "summary": "택배|상자|문앞"}')
    assert (parsed.purpose, parsed.summary) == ("DELIVERY", "택배|상자|문앞")


def test_few_shot_summaries_only_restate_what_was_said():
    # The model copies the examples' style; examples that add words teach it to invent.
    for shot in CATALOG.few_shots:
        assert is_grounded(shot["summary"], shot["transcript"]), shot


# R3 minor: eval sentences must not repeat the LLM examples.
def test_eval_cases_are_disjoint_from_few_shots():
    import json
    from pathlib import Path

    cases = Path(__file__).resolve().parent.parent / "eval" / "purpose_cases.jsonl"
    texts = {json.loads(line)["transcript"] for line in cases.read_text().splitlines() if line.strip()}
    shots = {s["transcript"] for s in CATALOG.few_shots}
    assert not texts & shots
