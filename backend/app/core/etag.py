from datetime import datetime

from fastapi import Response

from app.core.errors import AppError


def etag_for(obj_id: int, updated_at: datetime) -> str:
    return f'W/"{obj_id}-{int(updated_at.timestamp() * 1_000_000)}"'


def set_etag(response: Response, obj_id: int, updated_at: datetime) -> None:
    response.headers["ETag"] = etag_for(obj_id, updated_at)


def check_if_match(if_match: str | None, obj_id: int, updated_at: datetime) -> None:
    """If-Match is optional; when sent it must match, which prevents lost updates (DECISIONS.md #8)."""
    if if_match and if_match != "*" and if_match != etag_for(obj_id, updated_at):
        raise AppError(412, "stale_record", "This record was changed by someone else. Reload and try again.")
