"""Production hardening (docs/hardening.md): busy GPU, stuck inference, request log, settings, API key."""

import logging
import threading
import time

import pydantic
import pytest

from app.config import Settings
from app.errors import ApiError
from app.gpu import GpuSlot
from app.schemas import Analysis, Detection
from tests.conftest import ready_client
from tests.fixtures.make_fixtures import tiny_jpeg, tone_wav


# ── #3 bounded wait for a busy model ─────────────────────────────────────────


def test_slot_refuses_after_waiting_instead_of_queueing_forever():
    slot = GpuSlot("vision", wait_s=0.05)
    with slot():
        start = time.monotonic()
        with pytest.raises(ApiError) as err:
            with slot():
                pass
    assert err.value.status == 503 and err.value.code == "MODEL_BUSY"
    assert time.monotonic() - start < 1


def test_slot_frees_after_an_error():
    slot = GpuSlot("vision", wait_s=0.05)
    with pytest.raises(ValueError):
        with slot():
            raise ValueError
    with slot():  # not left locked
        pass


class BusyVision:
    def detect(self, image):
        raise ApiError(503, "MODEL_BUSY", "busy")


def test_busy_vision_answers_503_model_busy():
    with ready_client(vision=BusyVision()) as client:
        r = client.post("/internal/v1/vision/detect", files={"image": ("a.jpg", tiny_jpeg(), "image/jpeg")})
    assert r.status_code == 503 and r.json()["code"] == "MODEL_BUSY"


class Transcribes:
    def transcribe(self, audio):
        return "택배 왔습니다"


class BusyLanguage:
    def analyze(self, transcript):
        raise ApiError(503, "MODEL_BUSY", "busy")


def test_busy_language_model_falls_back_to_rules_instead_of_failing():
    # A visitor still gets an answer: keyword rules decide while the LLM is busy.
    with ready_client(stt=Transcribes(), language=BusyLanguage()) as client:
        r = client.post("/internal/v1/audio/process", files={"audio": ("a.wav", tone_wav(1), "audio/wav")})
    assert r.status_code == 200
    assert r.json()["purpose"] == "DELIVERY" and r.json()["flags"] == ["RULES_FALLBACK"]


# ── #4 stuck inference shows on /health ─────────────────────────────────────


class StuckVision:
    def __init__(self):
        self.slot = GpuSlot("vision", wait_s=0.05)
        self.slot.started_at = time.monotonic() - 3600  # an inference "running" for an hour


def test_health_degraded_when_an_inference_is_stuck():
    with ready_client(vision=StuckVision()) as client:
        body = client.get("/health").json()
    assert body["status"] == "degraded" and body["stuck"] == ["vision"]


# ── #5 request log with request id, never content ───────────────────────────


class Says:
    def analyze(self, transcript):
        return Analysis(summary="택배 보관", purpose="DELIVERY", subtype="PARCEL")


def test_request_id_is_echoed_or_generated():
    with ready_client(language=Says()) as client:
        given = client.post("/internal/v1/language/analyze", json={"transcript": "택배"}, headers={"X-Request-ID": "ev-42"})
        made = client.post("/internal/v1/language/analyze", json={"transcript": "택배"})
    assert given.headers["X-Request-ID"] == "ev-42"
    assert len(made.headers["X-Request-ID"]) >= 8


def test_request_log_has_path_status_time_but_no_visitor_words(caplog):
    secret = "1102호 비밀번호는 4321"
    with caplog.at_level(logging.INFO, logger="app.access"), ready_client(language=Says()) as client:
        client.post("/internal/v1/language/analyze", json={"transcript": secret}, headers={"X-Request-ID": "ev-7"})
    lines = [r.getMessage() for r in caplog.records if r.name == "app.access"]
    assert any("ev-7" in m and "/internal/v1/language/analyze" in m and "200" in m and "ms" in m for m in lines)
    assert not any(secret in r.getMessage() for r in caplog.records)


# ── #6 build info on /health ────────────────────────────────────────────────


def test_health_reports_build(monkeypatch):
    monkeypatch.setenv("BUILD_COMMIT", "abc1234")
    with ready_client() as client:
        assert client.get("/health").json()["build"] == "abc1234"


# ── #7 settings out of range fail at start ──────────────────────────────────


@pytest.mark.parametrize("name, value", [("PACKAGE_CONF", "4"), ("PERSON_CONF", "-0.1"), ("LLM_MAX_NEW_TOKENS", "0")])
def test_settings_out_of_range_are_refused(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(pydantic.ValidationError):
        Settings()


# ── #9 optional shared key between Spring and the model service ──────────────


class Sees:
    def detect(self, image):
        return [Detection(label="person", confidence=0.9)]


def _detect(client, **headers):
    return client.post("/internal/v1/vision/detect", files={"image": ("a.jpg", tiny_jpeg(), "image/jpeg")}, headers=headers)


def test_without_api_key_setting_nothing_changes():
    with ready_client(vision=Sees()) as client:
        assert _detect(client).status_code == 200


def test_api_key_required_when_set(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "s3cret")
    with ready_client(vision=Sees()) as client:
        missing, wrong, right = _detect(client), _detect(client, **{"X-Api-Key": "nope"}), _detect(client, **{"X-Api-Key": "s3cret"})
        health = client.get("/health")
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["code"] == "UNAUTHORIZED"
    assert right.status_code == 200
    assert health.status_code == 200  # Docker healthcheck has no key


def test_slot_is_thread_safe_under_contention():
    slot, inside, peak = GpuSlot("stt", wait_s=5), [0], [0]
    lock = threading.Lock()

    def job():
        with slot():
            with lock:
                inside[0] += 1
                peak[0] = max(peak[0], inside[0])
            time.sleep(0.01)
            with lock:
                inside[0] -= 1

    threads = [threading.Thread(target=job) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak[0] == 1


class Crashes:
    def detect(self, image):
        raise RuntimeError("CUDA error: an illegal memory access was encountered")


def test_unexpected_error_is_still_logged_with_its_request_id(caplog):
    with caplog.at_level(logging.INFO, logger="app.access"), ready_client(
        vision=Crashes(), raise_server_exceptions=False
    ) as client:
        r = client.post(
            "/internal/v1/vision/detect",
            files={"image": ("a.jpg", tiny_jpeg(), "image/jpeg")},
            headers={"X-Request-ID": "ev-9"},
        )
    assert r.status_code == 500 and r.json()["code"] == "INFERENCE_FAILED"
    assert any("ev-9" in rec.getMessage() and " 500 " in rec.getMessage() for rec in caplog.records if rec.name == "app.access")
