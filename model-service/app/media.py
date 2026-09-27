"""Decode uploads in memory only. Audio never touches disk (Zero-Storage, API v1.3 §6.3)."""

import io
import struct

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.errors import ApiError

AUDIO_RATE = 16000
PCM, FLOAT, EXTENSIBLE = 1, 3, 0xFFFE
REQUIRED = "PCM 16-bit, mono, 16000Hz"
# Camera Module 3 full resolution is 4608x2592 ≈ 12 MP; allow headroom, refuse absurd sizes.
MAX_IMAGE_PIXELS = 40_000_000


def decode_jpeg(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        if image.format != "JPEG":
            raise ApiError(400, "INVALID_IMAGE", f"JPEG 이미지만 허용됩니다(받은 형식: {image.format}).")
        # Checked before decoding: the header alone gives the size, decoding a huge image costs GBs of RAM.
        width, height = image.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ApiError(
                400, "INVALID_IMAGE", f"이미지 해상도가 너무 큽니다({width}x{height}, 최대 {MAX_IMAGE_PIXELS // 1_000_000}MP)."
            )
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ApiError(400, "INVALID_IMAGE", "이미지를 읽을 수 없습니다. JPEG 파일이어야 합니다.")


def _invalid_audio(message: str) -> ApiError:
    return ApiError(400, "INVALID_AUDIO", message)


def _read_riff(data: bytes) -> tuple[tuple[int, int, int, int], bytes]:
    """Return ((format tag, channels, rate, bits), sample bytes).

    Parsed by hand instead of the stdlib `wave` module, which rejects float and
    WAVE_FORMAT_EXTENSIBLE files without saying what they are.
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise _invalid_audio(f"WAV 파일을 읽을 수 없습니다({REQUIRED} 필요).")
    fmt = samples = None
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        (size,) = struct.unpack_from("<I", data, pos + 4)
        body = data[pos + 8 : pos + 8 + size]
        if chunk_id == b"fmt " and len(body) >= 16:
            tag, channels, rate, _, _, bits = struct.unpack_from("<HHIIHH", body)
            if tag == EXTENSIBLE and len(body) >= 26:
                (tag,) = struct.unpack_from("<H", body, 24)  # first field of the SubFormat GUID
            fmt = (tag, channels, rate, bits)
        elif chunk_id == b"data":
            samples = body
        pos += 8 + size + (size & 1)
    if fmt is None or samples is None:
        raise _invalid_audio(f"WAV 파일을 읽을 수 없습니다({REQUIRED} 필요).")
    return fmt, samples


def decode_wav(data: bytes) -> np.ndarray:
    (tag, channels, rate, bits), samples = _read_riff(data)
    if (tag, channels, rate, bits) != (PCM, 1, AUDIO_RATE, 16):
        kind = {PCM: "PCM", FLOAT: "float"}.get(tag, f"format {tag}")
        received = f"{kind} {bits}-bit, {channels}ch, {rate}Hz"
        raise _invalid_audio(f"지원하지 않는 음성 형식입니다: {received} → {REQUIRED} 필요.")
    samples = samples[: len(samples) - len(samples) % 2]
    if not samples:
        raise _invalid_audio("음성 데이터가 비어 있습니다.")
    return np.frombuffer(samples, dtype="<i2").astype(np.float32) / 32768.0
