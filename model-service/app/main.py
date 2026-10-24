import hmac
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartParser

from app.config import Settings
from app.errors import error_body, install_error_handlers
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
        return JSONResponse(status_code=400, content=error_body("INVALID_REQUEST", message))

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


access_log = logging.getLogger("app.access")
REQUEST_ID_UNSAFE = re.compile(r"[^A-Za-z0-9._:-]")


class RequestLog:
    """Plain ASGI middleware: request id, optional shared key, one log line per request.

    The line has the id, path, status and time only — never the photo, audio or transcript
    (visitors' words are personal data). Spring can pass its own X-Request-ID to join both logs.
    """

    def __init__(self, app, api_key: str = ""):
        self.app = app
        self.api_key = api_key.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        # Caller-supplied, so keep it to a safe charset and length (it goes into logs and a header).
        rid = REQUEST_ID_UNSAFE.sub("", headers.get(b"x-request-id", b"").decode("latin-1"))[:64]
        rid = rid or uuid.uuid4().hex[:12]
        start, status = time.perf_counter(), [0]

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                status[0] = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode("latin-1"))]
            await send(message)

        path = scope["path"]
        try:
            if self.api_key and path.startswith("/internal/") and not hmac.compare_digest(
                headers.get(b"x-api-key", b""), self.api_key
            ):
                body = error_body("UNAUTHORIZED", "X-Api-Key가 없거나 맞지 않습니다.")
                await JSONResponse(status_code=401, content=body)(scope, receive, send_with_id)
            else:
                await self.app(scope, receive, send_with_id)
        except Exception:
            status[0] = status[0] or 500  # Starlette answers it with 500 outside this middleware
            raise
        finally:  # "-" = no response sent (client went away)
            ms = (time.perf_counter() - start) * 1000
            access_log.info("rid=%s %s %s %s %.0fms", rid, scope["method"], path, status[0] or "-", ms)


def create_app(
    registry_factory: Callable[[Settings], ModelRegistry] | None = None,
) -> FastAPI:
    settings = Settings()
    if not logging.getLogger().handlers:  # uvicorn configures only its own loggers
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mock = settings.model_profile == "mock"
    if registry_factory is None:
        if mock:
            from app.mock import load_mock_registry as registry_factory
        else:
            registry_factory = load_registry

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
    if mock:  # registered first, so its endpoints win over the real ones with the same path
        from app.mock import mock_router

        app.include_router(mock_router)
    app.include_router(router)

    app.add_middleware(UploadLimit)
    app.add_middleware(RequestLog, api_key=settings.model_api_key)  # added last = runs first

    @app.get("/health")
    async def health():  # async: must answer even while inference threads are busy
        registry = app.state.registry
        body = {"profile": settings.model_profile, "build": os.environ.get("BUILD_COMMIT", "dev")}
        if app.state.load_failed or (registry is not None and len(registry.failed) == 3):
            return {"status": "error", **body}
        if registry is None or not registry.ready:
            return {"status": "loading", **body}
        stuck = registry.stuck(settings.stuck_after_s)
        if versions := registry.versions():
            body["models"] = versions
        if registry.failed:
            body["failed"] = list(registry.failed)
        if stuck:
            body["stuck"] = stuck
        if getattr(registry.vision, "package_mode", None):
            body["package_model"] = registry.vision.package_mode
        return {"status": "degraded" if registry.failed or stuck else "ok", **body}

    return app
