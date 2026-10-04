"""Mock model service: same API, canned answers, no GPU and no model weights.

For teammates who integrate with this service (Spring, Pi, app) on a laptop without a GPU.
Start with MODEL_PROFILE=mock (see Dockerfile.mock). Requests are validated exactly like the real
service (JPEG/WAV format, upload size, error bodies), so format mistakes show up early.

The answer is picked by a keyword in the uploaded file name:
  image: person, package, animal, empty (combine: "person_package.jpg"); no keyword → person.
         LOW_VISIBILITY is computed from the real image, as in the real service.
  audio: one of SCENARIOS below ("emergency.wav"); no keyword → delivery.
/language/analyze returns the canned answer for a scenario transcript, keyword rules otherwise.
"""

import time

from fastapi import APIRouter, File, Request, UploadFile

from app.config import Settings
from app.language.rules import rule_analyze
from app.media import decode_jpeg, decode_wav
from app.pipeline import analyze_transcript
from app.registry import ModelRegistry
from app.schemas import Analysis, AudioProcessResponse, Detection, DetectResponse, TranscribeResponse
from app.vision.quality import low_visibility

# Scenario → (transcript, purpose, subtype, summary, flags). Summaries follow the real model's
# style: 20 characters at most, only words the visitor said (API v1.5 §7.3).
SCENARIOS: dict[str, tuple[str, str, str | None, str, list[str]]] = {
    "delivery": ("택배 왔습니다. 문 앞에 놓고 갈게요.", "DELIVERY", "PARCEL", "택배 문 앞 보관", []),
    "food": ("배달의민족 주문하신 족발 왔습니다.", "DELIVERY", "FOOD", "족발 배달", []),
    "mail": ("우체국입니다. 등기우편 왔어요.", "DELIVERY", "MAIL", "우체국 등기우편", []),
    "pickup": ("반품 수거하러 왔습니다. 상자 가져갈게요.", "PICKUP", None, "반품 상자 수거", []),
    "personal": ("엄마 나야, 문 좀 열어줘.", "PERSONAL_VISIT", None, "가족 방문", []),
    "service": ("가스 점검 나왔습니다.", "SERVICE_VISIT", None, "가스 점검", []),
    "emergency": ("화재 신고 들어와서 소방서에서 나왔습니다.", "PUBLIC_EMERGENCY", None, "소방서 화재 확인", []),
    "threat": ("문 안 열면 부숴버린다.", "SAFETY_REVIEW", None, "문 부순다는 위협", []),
    "solicit": ("정수기 렌탈 홍보하러 왔습니다.", "SOLICITATION", None, "정수기 렌탈 홍보", []),
    "wrong": ("어, 죄송합니다. 호수를 잘못 눌렀네요.", "WRONG_VISIT", None, "호수 잘못 누름", []),
    "unknown": ("저기요, 잠깐만요.", "UNKNOWN", None, "저기요, 잠깐만요.", ["SUMMARY_FROM_TRANSCRIPT"]),
    "silent": ("", "UNKNOWN", None, "", ["NO_SPEECH"]),
}
DEFAULT_SCENARIO = "delivery"
VISION_SCORES = {"person": 0.91, "package": 0.78, "animal": 0.86}
CANNED = {t: Analysis(purpose=p, subtype=s, summary=m, flags=f) for t, p, s, m, f in SCENARIOS.values() if t}


def scenario_for(filename: str | None) -> str:
    name = (filename or "").lower()
    return next((key for key in SCENARIOS if key in name), DEFAULT_SCENARIO)


def detections_for(filename: str | None) -> list[Detection]:
    name = (filename or "").lower()
    if "empty" in name:
        return []
    labels = [label for label in VISION_SCORES if label in name] or ["person"]
    return [Detection(label=label, confidence=VISION_SCORES[label]) for label in labels]


class MockSpeech:
    """Stands in for STT; the transcript itself comes from the file name (see mock_router)."""

    def transcribe(self, audio) -> str:
        return SCENARIOS[DEFAULT_SCENARIO][0]


class MockLanguage:
    def analyze(self, transcript: str) -> Analysis:
        return CANNED.get(transcript) or rule_analyze(transcript)


def load_mock_registry(settings: Settings) -> ModelRegistry:
    return ModelRegistry(vision=object(), stt=MockSpeech(), language=MockLanguage(), ready=True)


mock_router = APIRouter(prefix="/internal/v1")


def _pause(request: Request) -> None:
    # MOCK_DELAY_MS adds waiting time, so callers can try their timeouts (real lite p95: audio 1.5 s).
    delay = request.app.state.settings.mock_delay_ms
    if delay:
        time.sleep(delay / 1000)


@mock_router.post("/vision/detect", response_model=DetectResponse)
def detect(request: Request, image: UploadFile = File(...)):
    picture = decode_jpeg(image.file.read())
    _pause(request)
    detections = detections_for(image.filename)
    seen_person = any(d.label == "person" for d in detections)
    flags = ["LOW_VISIBILITY"] if low_visibility(picture) and not seen_person else []
    return DetectResponse(detections=detections, flags=flags)


@mock_router.post("/speech/transcribe", response_model=TranscribeResponse)
def transcribe(request: Request, audio: UploadFile = File(...)):
    decode_wav(audio.file.read())
    _pause(request)
    return TranscribeResponse(transcript=SCENARIOS[scenario_for(audio.filename)][0])


@mock_router.post("/audio/process", response_model=AudioProcessResponse)
def audio_process(request: Request, audio: UploadFile = File(...)):
    decode_wav(audio.file.read())
    _pause(request)
    transcript = SCENARIOS[scenario_for(audio.filename)][0]
    analysis = analyze_transcript(MockLanguage(), transcript)
    return AudioProcessResponse(transcript=transcript, **analysis.model_dump())
