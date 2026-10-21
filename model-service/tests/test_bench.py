from bench.benchmark import TARGETS_MS, judge, percentile, timed


def test_timed_cycles_inputs_and_reports_first_call_separately():
    seen = []
    stats = timed(seen.append, ["a", "b", "c"], runs=5)
    assert seen == ["a", "a", "b", "c", "a", "b"]  # first (cold) call, then 5 timed runs cycling inputs
    assert set(stats) == {"first", "p50", "p95"}


def test_percentile_nearest_rank():
    samples = list(range(1, 21))  # 1..20
    assert percentile(samples, 50) == 10
    assert percentile(samples, 95) == 19
    assert percentile([7.0], 95) == 7.0


def test_judge_lite_only_checks_audio():
    stats = {"audio_process": {"p95": 3900}, "vision": {"p95": 900}}
    assert judge("lite", stats) == {"audio_process": True}


def test_judge_full_checks_audio_and_vision():
    stats = {"audio_process": {"p95": 2100}, "vision": {"p95": 250}}
    assert judge("full", stats) == {"audio_process": False, "vision": True}


def test_targets_match_plan():
    assert TARGETS_MS == {"lite": {"audio_process": 4000}, "full": {"audio_process": 2000, "vision": 300}}
