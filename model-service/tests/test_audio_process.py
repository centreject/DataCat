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

    def transcribe(self, audio):
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


def test_process_audio_stt_not_ready():
    lm = FakeLanguage(Analysis(summary="x", purpose="ETC"))
    with ready_client(stt=None, language=lm) as client:
        response = post_audio(client, tone_wav(1))
    assert response.status_code == 503
    assert response.json()["code"] == "MODEL_NOT_READY"
