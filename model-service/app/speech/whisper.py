import ctypes
import importlib.util
import threading
from pathlib import Path

import numpy as np


def _preload_cuda12_libs() -> None:
    """CTranslate2 needs CUDA 12 cuBLAS/cuDNN, but torch ships CUDA 13 libraries.

    Load the CUDA 12 copies from the nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels by
    path, so their sonames are already resolved when CTranslate2 dlopens them.
    """
    for package, pattern in (("nvidia.cublas", "libcublas*.so.12"), ("nvidia.cudnn", "libcudnn*.so.9")):
        spec = importlib.util.find_spec(package)
        if spec is None:
            continue
        for location in spec.submodule_search_locations:
            # Longest names first, so libcublasLt is loaded before libcublas, which needs it.
            for lib in sorted(Path(location, "lib").glob(pattern), key=lambda p: (len(p.name), p.name), reverse=True):
                ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)


_preload_cuda12_libs()

from faster_whisper import WhisperModel  # noqa: E402

from app.config import Settings  # noqa: E402
from app.speech.filters import clean_segments  # noqa: E402

# Domain words bias decoding toward what visitors actually say at the door.
DOMAIN_PROMPT = "택배, 배달, 배송, 검침, 점검, 관리사무소, 방문"


class WhisperSpeech:
    def __init__(self, settings: Settings):
        self.model = WhisperModel(
            settings.stt_model,
            device="cuda",
            compute_type=settings.stt_compute_type,
            download_root=str(Path(settings.weights_dir) / "whisper"),
        )
        self.lock = threading.Lock()
        self.transcribe(np.zeros(16000, dtype=np.float32))  # warm-up

    def transcribe(self, audio: np.ndarray) -> str:
        with self.lock:
            segments, _ = self.model.transcribe(
                audio,
                language="ko",
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt=DOMAIN_PROMPT,
            )
            # `segments` is a lazy generator; decoding happens while iterating, so stay inside the lock.
            return clean_segments((s.text, s.no_speech_prob) for s in segments)
