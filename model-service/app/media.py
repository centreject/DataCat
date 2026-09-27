"""Decode uploads in memory only. Audio never touches disk (Zero-Storage, API v1.3 §6.3)."""

import io
import wave

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.errors import ApiError

AUDIO_RATE = 16000


def decode_jpeg(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        if image.format != "JPEG":
            raise ApiError(400, "INVALID_IMAGE", f"JPEG 이미지만 허용됩니다(받은 형식: {image.format}).")
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ApiError(400, "INVALID_IMAGE", "이미지를 읽을 수 없습니다. JPEG 파일이어야 합니다.")


def _invalid_audio(message: str) -> ApiError:
    return ApiError(400, "INVALID_AUDIO", message)


def decode_wav(data: bytes) -> np.ndarray:
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            pcm = w.readframes(frames)
    except (wave.Error, EOFError):
        raise _invalid_audio("WAV 파일을 읽을 수 없습니다(PCM 16-bit, 16000Hz, mono 필요).")

    if channels != 1:
        raise _invalid_audio(f"mono 음성만 허용됩니다(받은 채널 수: {channels}).")
    if rate != AUDIO_RATE:
        raise _invalid_audio(f"샘플레이트는 {AUDIO_RATE}Hz여야 합니다(받은 값: {rate}Hz).")
    if width != 2:
        raise _invalid_audio(f"PCM 16-bit만 허용됩니다(받은 값: {8 * width}-bit).")
    if frames == 0 or not pcm:
        raise _invalid_audio("음성 데이터가 비어 있습니다.")

    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
