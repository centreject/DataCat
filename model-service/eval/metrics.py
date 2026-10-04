"""Metrics shared by the eval scripts, plus the plan's accuracy targets (full profile, provisional)."""

import re

TARGETS = {
    "person_recall": 0.95,
    "package_recall": 0.85,
    "animal_recall": 0.90,
    "stt_cer_max": 0.15,
    "purpose_accuracy": 0.90,
    # Emergencies and threats must not slip through as ordinary visits (plan: "긴급·위험 신호 우선").
    "critical_recall": 0.95,
    "subtype_accuracy": 0.80,
    "summary_over_20_max": 0.0,
    # Summaries read as a noun phrase ("택배 문 앞 보관"), not a copied sentence (decided 2026-10-04).
    "summary_noun_style_min": 0.90,
}

# Sentence endings that mark a copied utterance rather than a noun phrase ("놓고 갈게요", "왔습니다").
_SENTENCE_END = re.compile(r"(요|니다|다|까|죠|네)[.!?…~]*$")


def noun_style(summary: str) -> bool:
    return bool(summary.strip()) and not _SENTENCE_END.search(summary.strip())


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate with spaces removed (Korean spacing is inconsistent in STT output)."""
    ref, hyp = reference.replace(" ", ""), hypothesis.replace(" ", "")
    return _edit_distance(ref, hyp) / max(len(ref), 1)


def per_class_scores(gold: list[str], pred: list[str], labels: list[str]) -> dict[str, tuple[float, float]]:
    """label -> (precision, recall); 0.0 when undefined."""
    scores = {}
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        predicted = sum(p == label for p in pred)
        actual = sum(g == label for g in gold)
        scores[label] = (tp / predicted if predicted else 0.0, tp / actual if actual else 0.0)
    return scores


def group_recall(gold: list[str], pred: list[str], group: set[str]) -> float:
    """Share of gold cases in `group` whose prediction is also in `group` (any member counts)."""
    hits = [p in group for g, p in zip(gold, pred) if g in group]
    return sum(hits) / len(hits) if hits else 0.0


def subtype_accuracy(gold: list[tuple[str, str | None]], pred: list[tuple[str, str | None]]) -> float:
    """Exact (purpose, subtype) match over cases that have a gold subtype."""
    pairs = [(g, p) for g, p in zip(gold, pred) if g[1] is not None]
    return sum(g == p for g, p in pairs) / len(pairs) if pairs else 0.0


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"
