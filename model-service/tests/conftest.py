import pytest


@pytest.fixture(autouse=True)
def _default_profile(monkeypatch):
    # Tests assume the default profile regardless of the developer's shell.
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
