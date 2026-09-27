"""Real-model checks. Run: pytest -m gpu tests/test_speech_gpu.py -v
TTS samples come from `python eval/make_tts_audio.py`; missing files skip."""

from pathlib import Path

import pytest

from app.config import DATA_DIR
from app.media import decode_wav
from tests.fixtures.make_fixtures import silence_wav, tone_wav

pytestmark = pytest.mark.gpu

TTS = DATA_DIR / "audio" / "tts"


@pytest.fixture(scope="module")
def stt(gpu_registry):
    return gpu_registry.stt


def test_silence_gives_empty(stt):
    assert stt.transcribe(decode_wav(silence_wav(3))) == ""


def test_pure_tone_gives_empty(stt):
    assert stt.transcribe(decode_wav(tone_wav(3))) == ""


def test_korean_tts_sample(stt):
    path = TTS / "delivery_01.wav"
    if not path.exists():
        pytest.skip(f"missing {path.relative_to(DATA_DIR.parent)} (run eval/make_tts_audio.py)")
    assert "택배" in stt.transcribe(decode_wav(path.read_bytes()))


def test_load_registry_loads_stt(gpu_registry):
    from app.speech.whisper import WhisperSpeech

    assert isinstance(gpu_registry.stt, WhisperSpeech)
