"""Unit tests for docker/smoke.py fallback inputs and X-Api-Key header handling."""

import importlib.util
import io
import json
import urllib.request
from pathlib import Path

from app.media import decode_jpeg, decode_wav


def _load_smoke():
    path = Path(__file__).resolve().parent.parent / "docker" / "smoke.py"
    spec = importlib.util.spec_from_file_location("model_service_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sample_jpeg_falls_back_to_valid_jpeg_without_data_dir(monkeypatch, tmp_path):
    smoke = _load_smoke()
    monkeypatch.setattr(smoke, "DATA", tmp_path)
    raw = smoke.sample_jpeg()
    assert raw.startswith(b"\xff\xd8")
    image = decode_jpeg(raw)
    assert image.size == (16, 16)


def test_sample_wav_falls_back_to_valid_wav_without_files(monkeypatch, tmp_path):
    smoke = _load_smoke()
    monkeypatch.setattr(smoke, "DATA", tmp_path)
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    raw = smoke.sample_wav()
    samples = decode_wav(raw)
    assert samples.size == 16000


def test_request_sends_api_key_header_only_when_given(monkeypatch):
    smoke = _load_smoke()
    seen = []

    class FakeResponse(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def fake_urlopen(req, timeout=60):
        seen.append({k.lower(): v for k, v in req.header_items()})
        return FakeResponse(json.dumps({"status": "ok"}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert smoke.request("http://localhost:8000/health") == (200, {"status": "ok"})
    assert smoke.request("http://localhost:8000/internal/v1/language/analyze", b"{}", "application/json", "s3cret") == (
        200,
        {"status": "ok"},
    )
    assert "x-api-key" not in seen[0]
    assert seen[1]["x-api-key"] == "s3cret"
    assert seen[1]["content-type"] == "application/json"
