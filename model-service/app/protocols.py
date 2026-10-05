from typing import Protocol

import numpy as np
from PIL.Image import Image

from app.schemas import Analysis, Detection


class VisionModel(Protocol):
    def detect(self, image: Image) -> list[Detection]: ...


class SpeechModel(Protocol):
    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono samples at 16 kHz in [-1, 1]."""
        ...


class LanguageModel(Protocol):
    def analyze(self, transcript: str) -> Analysis: ...
