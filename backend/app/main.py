from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, health
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def _init_sentry(dsn: str | None) -> None:
    if not dsn:
        return
    try:
        import sentry_sdk  # optional dependency, only when a DSN is configured

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
    except ImportError:  # pragma: no cover
        import logging

        logging.getLogger("floorpulse").warning("FP_SENTRY_DSN set but sentry-sdk is not installed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    s = get_settings()
    sched = None
    if s.scheduler_enabled and s.env != "test":
        from app.jobs.runner import start_scheduler

        sched = start_scheduler()
    yield
    if sched:
        sched.shutdown(wait=False)


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    _init_sentry(s.sentry_dsn)
    app = FastAPI(
        title="FloorPulse API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/api/v1/openapi.json",
    )
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-CSRF-Token",
            "X-Device-Token",
            "If-Match",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["ETag", "X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware, max_body=s.max_request_bytes)

    app.include_router(health.router)
    api = APIRouter(prefix="/api/v1")
    for r in (auth.router, admin.router):
        api.include_router(r)
    app.include_router(api)
    return app


app = create_app()
