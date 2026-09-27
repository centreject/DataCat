from fastapi import APIRouter, File, Request, UploadFile

from app.errors import ApiError
from app.media import decode_jpeg
from app.registry import ModelRegistry
from app.schemas import Analysis, AnalyzeRequest, DetectResponse

router = APIRouter(prefix="/internal/v1")


def require(registry: ModelRegistry | None, name: str):
    model = getattr(registry, name, None) if registry is not None and registry.ready else None
    if model is None:
        raise ApiError(503, "MODEL_NOT_READY", f"{name} 모델이 아직 준비되지 않았습니다.")
    return model


@router.post("/vision/detect", response_model=DetectResponse)
def detect(request: Request, image: UploadFile = File(...)):
    # Sync handler: FastAPI runs it in a worker thread, so GPU inference doesn't block the event loop.
    model = require(request.app.state.registry, "vision")
    return DetectResponse(detections=model.detect(decode_jpeg(image.file.read())))


@router.post("/language/analyze", response_model=Analysis)
def analyze(request: Request, body: AnalyzeRequest):
    model = require(request.app.state.registry, "language")
    return model.analyze(body.transcript)
