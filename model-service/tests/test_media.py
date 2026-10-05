import numpy as np
import pytest

from app.errors import ApiError
from app.media import decode_jpeg, decode_wav
from tests.fixtures.make_fixtures import (
    EXTENSIBLE_TAG,
    FLOAT_TAG,
    raw_wav,
    silence_wav,
    tiny_jpeg,
    tone_wav,
)


def assert_api_error(exc_info, code: str, fragment: str | None = None):
    err = exc_info.value
    assert err.status == 400
    assert err.code == code
    if fragment is not None:
        assert fragment in err.message


def test_decode_wav_ok():
    audio = decode_wav(tone_wav(1))
    assert audio.shape == (16000,)
    assert audio.dtype == np.float32
    assert np.abs(audio).max() <= 1.0
    assert np.abs(audio).max() > 0.1


def test_decode_wav_rejects_stereo():
    with pytest.raises(ApiError) as e:
        decode_wav(tone_wav(1, channels=2))
    assert_api_error(e, "INVALID_AUDIO", "mono")


def test_decode_wav_rejects_44100():
    with pytest.raises(ApiError) as e:
        decode_wav(tone_wav(1, rate=44100))
    assert_api_error(e, "INVALID_AUDIO", "16000")


def test_decode_wav_rejects_32bit():
    with pytest.raises(ApiError) as e:
        decode_wav(tone_wav(1, sampwidth=4))
    assert_api_error(e, "INVALID_AUDIO", "16-bit")


def test_decode_wav_float_stereo_names_every_problem():
    data = np.zeros(2 * 44100, dtype="<f4").tobytes()
    with pytest.raises(ApiError) as e:
        decode_wav(raw_wav(FLOAT_TAG, channels=2, rate=44100, bits=32, data=data))
    assert_api_error(e, "INVALID_AUDIO")
    # Says what was received, not only what is required.
    for fragment in ("float", "2ch", "44100", "16-bit", "mono", "16000"):
        assert fragment in e.value.message


def test_decode_wav_accepts_extensible_pcm16():
    samples = (np.arange(16000) % 100).astype("<i2")
    audio = decode_wav(raw_wav(EXTENSIBLE_TAG, channels=1, rate=16000, bits=16, data=samples.tobytes()))
    assert audio.shape == (16000,)
    assert audio.dtype == np.float32


def test_decode_wav_rejects_extensible_float():
    data = np.zeros(16000, dtype="<f4").tobytes()
    with pytest.raises(ApiError) as e:
        decode_wav(raw_wav(EXTENSIBLE_TAG, 1, 16000, 32, data, subformat_tag=FLOAT_TAG))
    assert_api_error(e, "INVALID_AUDIO", "float")


def test_decode_wav_rejects_garbage():
    with pytest.raises(ApiError) as e:
        decode_wav(b"not a wav")
    assert_api_error(e, "INVALID_AUDIO")


def test_decode_wav_rejects_empty():
    with pytest.raises(ApiError) as e:
        decode_wav(silence_wav(0))
    assert_api_error(e, "INVALID_AUDIO")


def test_decode_jpeg_ok():
    image = decode_jpeg(tiny_jpeg())
    assert image.mode == "RGB"
    assert image.size == (8, 8)


def test_decode_jpeg_rejects_png():
    with pytest.raises(ApiError) as e:
        decode_jpeg(tiny_jpeg("PNG"))
    assert_api_error(e, "INVALID_IMAGE")


def test_decode_jpeg_rejects_decompression_bomb(monkeypatch):
    # Pillow raises DecompressionBombError (not OSError) above 2 × MAX_IMAGE_PIXELS.
    from PIL import Image

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ApiError) as e:
        decode_jpeg(tiny_jpeg())  # 8×8 = 64 px > 2 × 10
    assert_api_error(e, "INVALID_IMAGE")


def test_decode_jpeg_rejects_resolution_over_limit(monkeypatch):
    import app.media

    monkeypatch.setattr(app.media, "MAX_IMAGE_PIXELS", 32)
    with pytest.raises(ApiError) as e:
        decode_jpeg(tiny_jpeg())  # 64 px
    assert_api_error(e, "INVALID_IMAGE", "8x8")


def test_decode_jpeg_rejects_garbage():
    with pytest.raises(ApiError) as e:
        decode_jpeg(b"\xff\xd8\xff not really")
    assert_api_error(e, "INVALID_IMAGE")
