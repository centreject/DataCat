import pytest

import json
from pathlib import Path

from eval.metrics import cer, group_recall, noun_style, per_class_scores, subtype_accuracy

EVAL = Path(__file__).resolve().parent.parent / "eval"


def test_noun_style_rejects_copied_sentences():
    assert noun_style("택배 문 앞 보관") and noun_style("윗집 잘못 눌렀음") and noun_style("문 부순다는 위협")
    assert not noun_style("택배 문 앞 놓고 갈게요") and not noun_style("가스 점검 나왔습니다.")
    assert not noun_style("")


def test_heldout_set_does_not_overlap_dev_set_or_few_shots():
    from app.language.purposes import CATALOG

    def transcripts(name):
        return [json.loads(line)["transcript"] for line in (EVAL / name).read_text("utf-8").splitlines() if line.strip()]

    heldout = transcripts("heldout_cases.jsonl")
    assert len(heldout) == len(set(heldout))
    taken = set(transcripts("purpose_cases.jsonl")) | {s["transcript"] for s in CATALOG.few_shots}
    assert not taken & set(heldout)


def test_cer_identical_is_zero():
    assert cer("택배 왔습니다", "택배 왔습니다") == 0.0


def test_cer_ignores_spaces():
    assert cer("택배 왔습니다", "택배왔 습니다") == 0.0


def test_cer_one_substitution():
    # 6 characters without spaces, one wrong
    assert cer("택배왔습니다", "택배왔습니까") == pytest.approx(1 / 6)


def test_cer_empty_hypothesis_is_one():
    assert cer("택배", "") == 1.0


def test_cer_counts_insertions():
    assert cer("택배", "택배요") == pytest.approx(1 / 2)


def test_group_recall_counts_any_label_in_the_group():
    # Missing an emergency or a threat is the costly error; both labels count as "caught".
    gold = ["PUBLIC_EMERGENCY", "SAFETY_REVIEW", "SAFETY_REVIEW", "DELIVERY"]
    pred = ["SAFETY_REVIEW", "SAFETY_REVIEW", "UNKNOWN", "PUBLIC_EMERGENCY"]
    assert group_recall(gold, pred, {"PUBLIC_EMERGENCY", "SAFETY_REVIEW"}) == pytest.approx(2 / 3)


def test_subtype_accuracy_only_over_cases_with_a_gold_subtype():
    gold = [("DELIVERY", "FOOD"), ("DELIVERY", "PARCEL"), ("PICKUP", None)]
    pred = [("DELIVERY", "FOOD"), ("DELIVERY", "OTHER"), ("PICKUP", None)]
    assert subtype_accuracy(gold, pred) == pytest.approx(0.5)


def test_per_class_scores():
    gold = ["DELIVERY", "DELIVERY", "VISIT", "ETC"]
    pred = ["DELIVERY", "VISIT", "VISIT", "DELIVERY"]
    scores = per_class_scores(gold, pred, ["DELIVERY", "VISIT", "ETC"])
    assert scores["DELIVERY"] == pytest.approx((0.5, 0.5))  # (precision, recall)
    assert scores["VISIT"] == pytest.approx((0.5, 1.0))
    assert scores["ETC"] == pytest.approx((0.0, 0.0))
