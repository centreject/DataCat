import pytest

from app.hub_cache import load_cached_first


def test_uses_cache_without_network_when_available():
    calls = []

    def load(*, local_files_only: bool):
        calls.append(local_files_only)
        return "model"

    assert load_cached_first(load) == "model"
    assert calls == [True]


@pytest.mark.parametrize("missing", [FileNotFoundError("no cache"), OSError("not found"), ValueError("no snapshot")])
def test_downloads_only_when_cache_missing(missing):
    calls = []

    def load(*, local_files_only: bool):
        calls.append(local_files_only)
        if local_files_only:
            raise missing
        return "downloaded"

    assert load_cached_first(load) == "downloaded"
    assert calls == [True, False]


def test_other_errors_are_not_swallowed():
    def load(*, local_files_only: bool):
        raise RuntimeError("CUDA out of memory")

    with pytest.raises(RuntimeError):
        load_cached_first(load)
