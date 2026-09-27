import os
import tempfile

import pytest

from app.schemas import Analysis
from tests.conftest import ready_client
from tests.fixtures.make_fixtures import tone_wav

URL = "/internal/v1/audio/process"


class FakeSpeech:
    def __init__(self, text: str):
        self.text = text
        self.samples = None

    def transcribe(self, audio):
        self.samples = len(audio)
        return self.text


class FakeLanguage:
    def __init__(self, result: Analysis):
        self.result = result

    def analyze(self, transcript: str) -> Analysis:
        return self.result


def post_audio(client, data: bytes):
    return client.post(URL, files={"audio": ("a.wav", data, "audio/wav")})


def test_process_audio_contract():
    stt = FakeSpeech("택배 문 앞에 두고 갑니다.")
    lm = FakeLanguage(Analysis(summary="택배 문 앞 보관", purpose="DELIVERY"))
    with ready_client(stt=stt, language=lm) as client:
        response = post_audio(client, tone_wav(1))
    assert response.status_code == 200
    assert response.json() == {
        "transcript": "택배 문 앞에 두고 갑니다.",
        "purpose": "DELIVERY",
        "summary": "택배 문 앞 보관",
    }


def test_process_audio_silence():
    lm = FakeLanguage(Analysis(summary="should not be used", purpose="VISIT"))
    with ready_client(stt=FakeSpeech(""), language=lm) as client:
        response = post_audio(client, tone_wav(1))
    assert response.json() == {"transcript": "", "purpose": "ETC", "summary": ""}


@pytest.fixture
def no_disk(monkeypatch, tmp_path):
    """Fail loudly if anything tries to put the upload (or anything else) on disk."""

    def forbidden(*args, **kwargs):
        raise AssertionError("audio must not be written to disk")

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", forbidden)
    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbidden)
    monkeypatch.setattr(tempfile, "TemporaryFile", forbidden)
    monkeypatch.chdir(tmp_path)
    before = (set(os.listdir(tempfile.gettempdir())), set(os.listdir(tmp_path)))
    yield
    assert (set(os.listdir(tempfile.gettempdir())), set(os.listdir(tmp_path))) == before


@pytest.mark.parametrize("seconds", [5, 60])  # 60 s ≈ 1.9 MB, above Starlette's default 1 MB spool
def test_process_audio_writes_no_files(no_disk, seconds):
    stt = FakeSpeech("택배 왔습니다")
    lm = FakeLanguage(Analysis(summary="택배 도착", purpose="DELIVERY"))
    with ready_client(stt=stt, language=lm) as client:
        response = post_audio(client, tone_wav(seconds))
    assert response.status_code == 200


def test_chunked_upload_over_limit_is_rejected_without_disk(monkeypatch):
    # Record (not block) disk spills: blocking would itself turn into a 400 and hide the bug.
    spills = []
    original = tempfile.SpooledTemporaryFile.rollover

    def spy(self):
        spills.append(self)
        return original(self)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", spy)
    # Spring's WebClient may stream multipart with Transfer-Encoding: chunked (no Content-Length).
    boundary = "b0undary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="a.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode()

    def body():
        yield head
        for _ in range(17):
            yield b"\x00" * (1024 * 1024)
        yield f"\r\n--{boundary}--\r\n".encode()

    stt = FakeSpeech("x")
    lm = FakeLanguage(Analysis(summary="x", purpose="ETC"))
    with ready_client(stt=stt, language=lm) as client:
        response = client.post(
            URL, content=body(), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
    assert spills == []
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_long_audio_is_trimmed_to_30_seconds():
    # 240 s took ~6.4 s end to end on the 3060 Ti; the Pi gives up after 3-5 s.
    stt = FakeSpeech("택배 왔습니다")
    lm = FakeLanguage(Analysis(summary="택배 도착", purpose="DELIVERY"))
    with ready_client(stt=stt, language=lm) as client:
        response = post_audio(client, tone_wav(120))
    assert response.status_code == 200
    assert stt.samples == 30 * 16000


def test_short_audio_is_not_trimmed():
    stt = FakeSpeech("x")
    lm = FakeLanguage(Analysis(summary="x", purpose="ETC"))
    with ready_client(stt=stt, language=lm) as client:
        post_audio(client, tone_wav(5))
    assert stt.samples == 5 * 16000


def test_process_audio_uses_rules_when_llm_failed_to_load():
    with ready_client(stt=FakeSpeech("택배 왔습니다"), language=None) as client:
        response = post_audio(client, tone_wav(1))
    assert response.status_code == 200
    assert response.json() == {"transcript": "택배 왔습니다", "purpose": "DELIVERY", "summary": "택배 왔습니다"}


def test_process_audio_stt_not_ready():
    lm = FakeLanguage(Analysis(summary="x", purpose="ETC"))
    with ready_client(stt=None, language=lm) as client:
        response = post_audio(client, tone_wav(1))
    assert response.status_code == 503
    assert response.json()["code"] == "MODEL_NOT_READY"
