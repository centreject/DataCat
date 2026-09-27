"""WhisperSpeech start-up behaviour with faster-whisper stubbed (no GPU)."""

from types import SimpleNamespace

import pytest

import app.speech.whisper as whisper_module
from app.config import Settings


class StubWhisperModel:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def transcribe(self, audio, **kwargs):
        call = {"kwargs": kwargs, "decoded": False}
        self.calls.append(call)

        def segments():  # faster-whisper decodes lazily, while the generator is consumed
            call["decoded"] = True
            yield SimpleNamespace(text="", no_speech_prob=0.9)

        return segments(), None


def test_warm_up_runs_the_decoder(monkeypatch):
    # A silent warm-up is dropped by VAD, so a broken cuBLAS/cuDNN would only fail on the first
    # real request while /health already says ok (review 2026-09-27).
    monkeypatch.setattr(whisper_module, "WhisperModel", StubWhisperModel)
    stt = whisper_module.WhisperSpeech(Settings())
    warm_up = stt.model.calls[0]
    assert warm_up["kwargs"]["vad_filter"] is False
    assert warm_up["decoded"] is True


def test_warm_up_failure_fails_loading(monkeypatch):
    class BrokenCuda(StubWhisperModel):
        def transcribe(self, audio, **kwargs):
            raise RuntimeError("Library libcublas.so.12 is not found")

    monkeypatch.setattr(whisper_module, "WhisperModel", BrokenCuda)
    with pytest.raises(RuntimeError):
        whisper_module.WhisperSpeech(Settings())
