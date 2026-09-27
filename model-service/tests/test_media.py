import numpy as np
import pytest

from app.errors import ApiError
from app.media import decode_jpeg, decode_wav
from tests.fixtures.make_fixtures import silence_wav, tiny_jpeg, tone_wav


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


def test_decode_jpeg_rejects_garbage():
    with pytest.raises(ApiError) as e:
        decode_jpeg(b"\xff\xd8\xff not really")
    assert_api_error(e, "INVALID_IMAGE")
