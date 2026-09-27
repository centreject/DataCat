import pytest

from eval.metrics import cer, per_class_scores


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


def test_per_class_scores():
    gold = ["DELIVERY", "DELIVERY", "VISIT", "ETC"]
    pred = ["DELIVERY", "VISIT", "VISIT", "DELIVERY"]
    scores = per_class_scores(gold, pred, ["DELIVERY", "VISIT", "ETC"])
    assert scores["DELIVERY"] == pytest.approx((0.5, 0.5))  # (precision, recall)
    assert scores["VISIT"] == pytest.approx((0.5, 1.0))
    assert scores["ETC"] == pytest.approx((0.0, 0.0))
