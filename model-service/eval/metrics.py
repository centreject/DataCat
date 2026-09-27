"""Metrics shared by the eval scripts, plus the plan's accuracy targets (full profile, provisional)."""

TARGETS = {
    "person_recall": 0.95,
    "package_recall": 0.85,
    "stt_cer_max": 0.15,
    "purpose_accuracy": 0.90,
    "summary_over_20_max": 0.0,
}


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


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"
