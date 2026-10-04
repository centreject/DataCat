import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.mock import SCENARIOS, MockLanguage, detections_for, scenario_for
from app.schemas import AudioProcessResponse
from docs.make_api_docs import render, sample_jpeg, sample_wav


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "mock")
    app = create_app()
    with TestClient(app) as c:
        app.state.loader.join(timeout=5)
        yield c


def post_image(client, name, jpeg=None):
    files = {"image": (name, jpeg or sample_jpeg(), "image/jpeg")}
    return client.post("/internal/v1/vision/detect", files=files)


def post_audio(client, name, wav=None, path="audio/process"):
    return client.post(f"/internal/v1/{path}", files={"audio": (name, wav or sample_wav(), "audio/wav")})


def test_health_ok_with_mock_profile(client):
    assert client.get("/health").json() == {"status": "ok", "profile": "mock"}


def test_vision_answer_follows_file_name(client):
    labels = [d["label"] for d in post_image(client, "door_person_package.jpg").json()["detections"]]
    assert labels == ["person", "package"]
    assert post_image(client, "x.jpg").json()["detections"][0]["label"] == "person"
    assert post_image(client, "empty.jpg").json() == {"detections": [], "flags": []}


def test_vision_low_visibility_from_real_image(client):
    body = post_image(client, "empty.jpg", sample_jpeg(textured=False)).json()
    assert body["flags"] == ["LOW_VISIBILITY"]


def test_every_audio_scenario_is_a_valid_response(client):
    for name, (transcript, purpose, subtype, *_rest) in SCENARIOS.items():
        body = post_audio(client, f"pi_{name}.wav").json()
        AudioProcessResponse(**body)
        assert (body["transcript"], body["purpose"], body["subtype"]) == (transcript, purpose, subtype)
    assert post_audio(client, "silent.wav").json()["flags"] == ["NO_SPEECH"]


def test_transcribe_and_analyze_agree_with_audio_process(client):
    transcript = post_audio(client, "food.wav", path="speech/transcribe").json()["transcript"]
    analyzed = client.post("/internal/v1/language/analyze", json={"transcript": transcript}).json()
    processed = post_audio(client, "food.wav").json()
    assert analyzed == {k: processed[k] for k in ("summary", "purpose", "subtype", "flags")}


def test_mock_rejects_wrong_audio_format_like_the_real_service(client):
    r = post_audio(client, "delivery.wav", sample_wav(rate=44100, channels=2))
    assert r.status_code == 400 and r.json()["code"] == "INVALID_AUDIO"


def test_unknown_transcript_uses_keyword_rules():
    assert MockLanguage().analyze("택배 왔어요").purpose == "DELIVERY"


def test_scenario_and_detection_defaults():
    assert scenario_for(None) == "delivery"
    assert [d.label for d in detections_for("CAT_animal.JPG")] == ["animal"]


def test_mock_starts_without_ml_libraries():
    code = (
        "import os, sys; os.environ['MODEL_PROFILE'] = 'mock'\n"
        "from fastapi.testclient import TestClient\nfrom app.main import create_app\n"
        "app = create_app()\nwith TestClient(app) as c:\n    app.state.loader.join(5)\n"
        "assert not {'torch', 'ultralytics', 'transformers', 'faster_whisper'} & set(sys.modules)\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_api_docs_are_up_to_date():
    stale = [path.name for path, text in render().items() if not path.exists() or path.read_text("utf-8") != text]
    assert not stale, f"run `python docs/make_api_docs.py` (stale: {stale})"
