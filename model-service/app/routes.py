from fastapi import APIRouter, File, Request, UploadFile

from app.errors import ApiError
from app.media import decode_jpeg, decode_wav
from app.pipeline import analyze_transcript, process_audio
from app.registry import ModelRegistry
from app.schemas import (
    Analysis,
    AnalyzeRequest,
    AudioProcessResponse,
    DetectResponse,
    TranscribeResponse,
)
from app.vision.quality import low_visibility

router = APIRouter(prefix="/internal/v1")


def require(registry: ModelRegistry | None, name: str):
    model = getattr(registry, name, None) if registry is not None and registry.ready else None
    if model is None:
        raise ApiError(503, "MODEL_NOT_READY", f"{name} 모델이 아직 준비되지 않았습니다.")
    return model


def require_loaded(registry: ModelRegistry | None) -> ModelRegistry:
    """For endpoints that can do without the LLM (keyword rules): only wait for loading to finish."""
    if registry is None or not registry.ready:
        raise ApiError(503, "MODEL_NOT_READY", "모델을 불러오는 중입니다.")
    return registry


@router.post("/vision/detect", response_model=DetectResponse)
def detect(request: Request, image: UploadFile = File(...)):
    # Sync handler: FastAPI runs it in a worker thread, so GPU inference doesn't block the event loop.
    model = require(request.app.state.registry, "vision")
    picture = decode_jpeg(image.file.read())
    detections = model.detect(picture)
    # If a person is seen, the camera is evidently not blocked, however dark the frame.
    seen_person = any(d.label == "person" for d in detections)
    flags = ["LOW_VISIBILITY"] if low_visibility(picture) and not seen_person else []
    return DetectResponse(detections=detections, flags=flags)


@router.post("/speech/transcribe", response_model=TranscribeResponse)
def transcribe(request: Request, audio: UploadFile = File(...)):
    model = require(request.app.state.registry, "stt")
    return TranscribeResponse(transcript=model.transcribe(decode_wav(audio.file.read())))


@router.post("/audio/process", response_model=AudioProcessResponse)
def audio_process(request: Request, audio: UploadFile = File(...)):
    registry = request.app.state.registry
    require(registry, "stt")  # the LLM is optional: keyword rules stand in if it failed to load
    return process_audio(registry, audio.file.read())


@router.post("/language/analyze", response_model=Analysis)
def analyze(request: Request, body: AnalyzeRequest):
    registry = require_loaded(request.app.state.registry)
    return analyze_transcript(registry.language, body.transcript)
