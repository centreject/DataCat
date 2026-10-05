from app.speech.filters import clean_segments
from tests.conftest import ready_client
from tests.fixtures.make_fixtures import tone_wav

URL = "/internal/v1/speech/transcribe"


class FakeSpeech:
    def __init__(self, text: str):
        self.text = text
        self.seen = None

    def transcribe(self, audio):
        self.seen = audio
        return self.text


def post_audio(client, data: bytes):
    return client.post(URL, files={"audio": ("a.wav", data, "audio/wav")})


def test_clean_drops_hallucination():
    assert clean_segments([("택배 왔습니다", 0.1), ("시청해 주셔서 감사합니다", 0.2)]) == "택배 왔습니다"


def test_clean_drops_high_no_speech():
    assert clean_segments([("음", 0.9)]) == ""


def test_clean_joins_segments_with_single_space():
    assert clean_segments([(" 택배 왔습니다. ", 0.1), (" 문 앞에 둘게요.", 0.2)]) == "택배 왔습니다. 문 앞에 둘게요."


def test_clean_drops_hallucination_variants():
    segments = [("시청해주셔서 감사합니다!", 0.1), ("구독과 좋아요 부탁드려요", 0.1), ("MBC 뉴스 이덕영입니다", 0.1)]
    assert clean_segments(segments) == ""


def test_clean_removes_broken_characters():
    # Whisper can cut a multi-byte token in half, leaving U+FFFD ("열어�" seen in eval, 2026-09-27).
    assert clean_segments([("엄마, 나야 문 좀 열어�", 0.1)]) == "엄마, 나야 문 좀 열어"


def test_transcribe_route():
    fake = FakeSpeech("택배 왔습니다.")
    with ready_client(stt=fake) as client:
        response = post_audio(client, tone_wav(1))
    assert response.status_code == 200
    assert response.json() == {"transcript": "택배 왔습니다."}
    assert fake.seen.shape == (16000,)


def test_transcribe_route_trims_long_audio():
    fake = FakeSpeech("x")
    with ready_client(stt=fake) as client:
        post_audio(client, tone_wav(45))
    assert fake.seen.shape == (30 * 16000,)


def test_transcribe_route_rejects_stereo():
    with ready_client(stt=FakeSpeech("x")) as client:
        response = post_audio(client, tone_wav(1, channels=2))
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_AUDIO"
