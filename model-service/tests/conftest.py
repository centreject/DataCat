from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import ModelRegistry


@pytest.fixture(autouse=True)
def _default_profile(monkeypatch):
    # Tests assume the default profile regardless of the developer's shell.
    monkeypatch.delenv("MODEL_PROFILE", raising=False)


@pytest.fixture(scope="session")
def gpu_registry():
    """Real models loaded once for the whole GPU test session (8 GB cards can't hold two copies)."""
    from app.config import Settings
    from app.registry import load_registry

    return load_registry(Settings())


@contextmanager
def ready_client(vision=None, stt=None, language=None):
    """TestClient whose registry is already loaded with the given (fake) models."""
    app = create_app(lambda s: ModelRegistry(vision=vision, stt=stt, language=language, ready=True))
    with TestClient(app) as client:
        app.state.loader.join(timeout=5)
        yield client
