"""Synthetic media for tests. Generated in memory; nothing is committed as binary."""

import io
import math
import struct
import wave

from PIL import Image


def tone_wav(seconds: float, rate: int = 16000, channels: int = 1, sampwidth: int = 2) -> bytes:
    frames = int(seconds * rate)
    peak = (2 ** (8 * sampwidth - 1)) - 1
    fmt = {1: "b", 2: "h", 4: "i"}[sampwidth]
    samples = []
    for i in range(frames):
        value = int(0.5 * peak * math.sin(2 * math.pi * 440 * i / rate))
        samples.extend([value] * channels)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}{fmt}", *samples))
    return buf.getvalue()


PCM_TAG, FLOAT_TAG, EXTENSIBLE_TAG = 1, 3, 0xFFFE
_PCM_SUBFORMAT = struct.pack("<H", PCM_TAG) + bytes.fromhex("000000001000800000aa00389b71")


def raw_wav(tag: int, channels: int, rate: int, bits: int, data: bytes, subformat_tag: int = PCM_TAG) -> bytes:
    """Hand-built RIFF/WAVE, for layouts the stdlib `wave` writer cannot produce (float, EXTENSIBLE)."""
    align = channels * bits // 8
    fmt = struct.pack("<HHIIHH", tag, channels, rate, rate * align, align, bits)
    if tag == EXTENSIBLE_TAG:
        sub = struct.pack("<H", subformat_tag) + _PCM_SUBFORMAT[2:]
        fmt += struct.pack("<HHI", 22, bits, 0) + sub
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


def silence_wav(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(seconds * 16000))
    return buf.getvalue()


def tiny_jpeg(fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 120, 40)).save(buf, format=fmt)
    return buf.getvalue()
