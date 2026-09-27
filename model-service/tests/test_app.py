import threading

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.registry import ModelRegistry


def blocking_factory(release: threading.Event):
    def factory(settings: Settings) -> ModelRegistry:
        release.wait(timeout=5)
        return ModelRegistry(vision=None, stt=None, language=None, ready=True)

    return factory


def test_health_reports_loading_then_ok():
    release = threading.Event()
    app = create_app(blocking_factory(release))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "loading", "profile": "lite"}
        release.set()
        app.state.loader.join(timeout=5)
        assert client.get("/health").json() == {"status": "ok", "profile": "lite"}


def test_health_reports_error_when_loading_fails():
    def failing(settings: Settings) -> ModelRegistry:
        raise RuntimeError("CUDA out of memory")

    app = create_app(failing)
    with TestClient(app) as client:
        app.state.loader.join(timeout=5)
        assert client.get("/health").json() == {"status": "error", "profile": "lite"}


def test_detect_while_loading_returns_503():
    release = threading.Event()
    app = create_app(blocking_factory(release))
    with TestClient(app) as client:
        response = client.post(
            "/internal/v1/vision/detect",
            files={"image": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
        release.set()
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "MODEL_NOT_READY"
    assert isinstance(body["message"], str) and body["message"]


def test_validation_error_uses_error_format():
    app = create_app(lambda s: ModelRegistry(vision=None, stt=None, language=None, ready=True))
    with TestClient(app) as client:
        response = client.post("/internal/v1/language/analyze", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_profile_derived_settings():
    assert Settings(model_profile="full").stt_compute_type == "float16"
    assert Settings().stt_compute_type == "int8_float16"
    assert Settings().llm_quantize_4bit is True
    assert Settings(model_profile="full").llm_quantize_4bit is False
