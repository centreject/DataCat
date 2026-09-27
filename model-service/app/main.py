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


class _UploadTooLarge(Exception):
    pass


class UploadLimit:
    """Plain ASGI middleware: reject requests over MAX_UPLOAD_BYTES before anything spills to disk.

    Checks Content-Length up front, and also counts body bytes as they arrive, because a chunked
    upload (Transfer-Encoding: chunked, no Content-Length) would otherwise pass the header check.
    """

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _too_large() -> JSONResponse:
        message = f"업로드가 너무 큽니다(최대 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)."
        return JSONResponse(status_code=400, content={"code": "INVALID_REQUEST", "message": message})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > MAX_UPLOAD_BYTES:
            await self._too_large()(scope, receive, send)
            return

        received = 0
        started = False

        async def counting_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_UPLOAD_BYTES:
                    raise _UploadTooLarge  # before the parser sees (and spools) this chunk
            return message

        async def tracking_send(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _UploadTooLarge:
            if not started:
                await self._too_large()(scope, receive, send)


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
    async def health():  # async: must answer even while inference threads are busy
        registry = app.state.registry
        body = {"profile": settings.model_profile}
        if app.state.load_failed or (registry is not None and len(registry.failed) == 3):
            status = "error"
        elif registry is None or not registry.ready:
            status = "loading"
        elif registry.failed:
            status = "degraded"
            body["failed"] = list(registry.failed)
        else:
            status = "ok"
        return {"status": status, **body}

    return app
