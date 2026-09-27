import threading
from pathlib import Path

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


def test_health_degraded_when_a_model_failed():
    registry = ModelRegistry(vision=object(), stt=object(), language=None, ready=True, failed=("language",))
    app = create_app(lambda s: registry)
    with TestClient(app) as client:
        app.state.loader.join(timeout=5)
        body = client.get("/health").json()
    assert body == {"status": "degraded", "profile": "lite", "failed": ["language"]}


def test_health_error_when_every_model_failed():
    registry = ModelRegistry(
        vision=None, stt=None, language=None, ready=True, failed=("vision", "stt", "language")
    )
    app = create_app(lambda s: registry)
    with TestClient(app) as client:
        app.state.loader.join(timeout=5)
        assert client.get("/health").json()["status"] == "error"


def test_load_registry_keeps_working_models_when_one_fails(monkeypatch):
    import app.language.qwen
    import app.speech.whisper
    import app.vision.yolo
    from app.config import Settings
    from app.registry import load_registry

    class Works:
        def __init__(self, settings):
            pass

    class OutOfMemory:
        def __init__(self, settings):
            raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(app.vision.yolo, "YoloVision", Works)
    monkeypatch.setattr(app.speech.whisper, "WhisperSpeech", Works)
    monkeypatch.setattr(app.language.qwen, "QwenLanguage", OutOfMemory)
    registry = load_registry(Settings())
    assert isinstance(registry.vision, Works) and isinstance(registry.stt, Works)
    assert registry.language is None
    assert registry.failed == ("language",)
    assert registry.ready is True


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


def test_unknown_path_uses_error_format():
    app = create_app(lambda s: ModelRegistry(vision=None, stt=None, language=None, ready=True))
    with TestClient(app) as client:
        response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["message"]


def test_wrong_method_uses_error_format():
    app = create_app(lambda s: ModelRegistry(vision=None, stt=None, language=None, ready=True))
    with TestClient(app) as client:
        response = client.get("/internal/v1/vision/detect")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_model_exception_returns_inference_failed():
    class Broken:
        def detect(self, image):
            raise RuntimeError("CUDA error")

    from tests.fixtures.make_fixtures import tiny_jpeg

    app = create_app(lambda s: ModelRegistry(vision=Broken(), stt=None, language=None, ready=True))
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.loader.join(timeout=5)
        response = client.post(
            "/internal/v1/vision/detect", files={"image": ("x.jpg", tiny_jpeg(), "image/jpeg")}
        )
    assert response.status_code == 500
    assert response.json()["code"] == "INFERENCE_FAILED"


def test_weights_dir_is_independent_of_working_directory(tmp_path, monkeypatch):
    service_root = Path(__file__).resolve().parent.parent
    monkeypatch.chdir(tmp_path)
    assert Path(Settings().weights_dir) == service_root / "data" / "weights"


def test_profile_derived_settings():
    assert Settings(model_profile="full").stt_compute_type == "float16"
    assert Settings().stt_compute_type == "int8_float16"
    assert Settings().llm_quantize_4bit is True
    assert Settings(model_profile="full").llm_quantize_4bit is False
