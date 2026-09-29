from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.core.deps import DB
from app.core.errors import AppError

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db: DB) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise AppError(503, "not_ready", "Database unavailable") from e
    return {"status": "ready"}


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
