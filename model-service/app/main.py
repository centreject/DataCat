import logging
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartParser

from app.config import Settings
from app.errors import install_error_handlers
from app.registry import ModelRegistry, load_registry
from app.routes import router

log = logging.getLogger(__name__)

# Uploads are spooled in memory up to this size; Starlette's default (1 MB ≈ 31 s of 16 kHz audio)
# would roll longer utterances over to a temp file on disk, breaking Zero-Storage (API v1.3 §6.3).
# Larger requests are rejected before parsing.
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MultiPartParser.spool_max_size = MAX_UPLOAD_BYTES


class UploadLimit:
    """Plain ASGI middleware: reject oversized requests by Content-Length before parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            length = dict(scope["headers"]).get(b"content-length", b"")
            if length.isdigit() and int(length) > MAX_UPLOAD_BYTES:
                message = f"업로드가 너무 큽니다(최대 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)."
                response = JSONResponse(status_code=400, content={"code": "INVALID_REQUEST", "message": message})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app(
    registry_factory: Callable[[Settings], ModelRegistry] = load_registry,
) -> FastAPI:
    settings = Settings()

    def load() -> None:
        try:
            app.state.registry = registry_factory(settings)
        except Exception:
            log.exception("model loading failed")
            app.state.load_failed = True

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load in the background so /health answers "loading" instead of blocking startup.
        app.state.loader = threading.Thread(target=load, daemon=True)
        app.state.loader.start()
        yield

    app = FastAPI(title="DataCat model service", lifespan=lifespan)
    app.state.settings = settings
    app.state.registry = None
    app.state.load_failed = False
    install_error_handlers(app)
    app.include_router(router)

    app.add_middleware(UploadLimit)

    @app.get("/health")
    def health():
        if app.state.load_failed:
            status = "error"
        elif app.state.registry is not None and app.state.registry.ready:
            status = "ok"
        else:
            status = "loading"
        return {"status": status, "profile": settings.model_profile}

    return app
