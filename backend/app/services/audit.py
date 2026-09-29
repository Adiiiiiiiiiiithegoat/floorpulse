import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.logging import client_ip_var, request_id_var
from app.models.audit import AuditLog
from app.models.org import User

_SECRET_FIELDS = {"password_hash", "pin_hash", "totp_secret", "token_hash", "key_hash"}


def _jsonable(v: Any) -> Any:
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, enum.Enum):
        return v.value
    return v


def snapshot(obj: Any) -> dict[str, Any]:
    """Column values of a mapped object, secrets redacted."""
    mapper = inspect(obj).mapper
    return {
        c.key: ("***" if c.key in _SECRET_FIELDS else _jsonable(getattr(obj, c.key)))
        for c in mapper.column_attrs
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return only the changed keys, ignoring updated_at."""
    keys = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k) and k != "updated_at"}
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


def record(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    *,
    org_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str | None = None,
) -> AuditLog:
    org = org_id if org_id is not None else (actor.organization_id if actor else None)
    if org is None:
        raise ValueError("audit record needs an organization")
    row = AuditLog(
        organization_id=org,
        actor_user_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=before,
        after=after,
        note=note,
        ip=client_ip_var.get(),
        request_id=request_id_var.get(),
    )
    db.add(row)
    return row
