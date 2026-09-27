import logging
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.errors import install_error_handlers
from app.registry import ModelRegistry, load_registry
from app.routes import router

log = logging.getLogger(__name__)


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
