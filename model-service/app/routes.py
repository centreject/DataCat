from fastapi import APIRouter, File, Request, UploadFile

from app.errors import ApiError
from app.registry import ModelRegistry
from app.schemas import Analysis, AnalyzeRequest, DetectResponse

router = APIRouter(prefix="/internal/v1")


def require(registry: ModelRegistry | None, name: str):
    model = getattr(registry, name, None) if registry is not None and registry.ready else None
    if model is None:
        raise ApiError(503, "MODEL_NOT_READY", f"{name} 모델이 아직 준비되지 않았습니다.")
    return model


@router.post("/vision/detect", response_model=DetectResponse)
async def detect(request: Request, image: UploadFile = File(...)):
    model = require(request.app.state.registry, "vision")
    raise ApiError(503, "MODEL_NOT_READY", "vision 엔드포인트가 아직 구현되지 않았습니다.")


@router.post("/language/analyze", response_model=Analysis)
def analyze(request: Request, body: AnalyzeRequest):
    model = require(request.app.state.registry, "language")
    return model.analyze(body.transcript)
