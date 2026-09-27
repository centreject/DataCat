from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Error that maps to the spec's {"code", "message"} response (API v1.3 §12)."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = {400: "INVALID_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(
            exc.status_code, f"HTTP_{exc.status_code}"
        )
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        fields = ", ".join(".".join(str(p) for p in e["loc"]) for e in exc.errors())
        return JSONResponse(
            status_code=400,
            content=_body("INVALID_REQUEST", f"요청 형식이 올바르지 않습니다: {fields}"),
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_body("INFERENCE_FAILED", "모델 추론 중 오류가 발생했습니다."),
        )
