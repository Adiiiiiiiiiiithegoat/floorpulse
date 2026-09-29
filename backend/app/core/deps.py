from collections.abc import Callable
from typing import Annotated, Any, Protocol, TypeVar

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError, forbidden, not_found
from app.core.security import decode_access_token
from app.models.org import Role, User

DB = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    token = creds.credentials if creds else None
    # EventSource cannot set headers, so the SSE stream alone may pass the token as a query param.
    if token is None and request.url.path.endswith("/stream"):
        token = request.query_params.get("access_token")
    if not token:
        raise AppError(401, "unauthorized", "Not authenticated")
    claims = decode_access_token(token)
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active or user.organization_id != claims.get("org"):
        raise AppError(401, "unauthorized", "Not authenticated")
    request.state.user = user
    request.state.device_id = claims.get("dev")
    request.state.session_id = claims.get("sid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[..., User]:
    """Admin passes every role check. Other users need at least one of `roles`."""
    allowed = set(roles) | {Role.admin}

    def _dep(user: CurrentUser) -> User:
        if not user.role_set & allowed:
            raise forbidden()
        return user

    return _dep


def has_role(user: User, *roles: Role) -> bool:
    return bool(user.role_set & (set(roles) | {Role.admin}))


# ---- tenancy ---------------------------------------------------------------------------------


class _TenantRow(Protocol):
    organization_id: Any


T = TypeVar("T")
S = TypeVar("S", bound=Select[Any])


def scoped(stmt: S, model: Any, user: User) -> S:
    """Every tenant query goes through here."""
    return stmt.where(model.organization_id == user.organization_id)


def get_owned(db: Session, model: type[T], obj_id: int, user: User, what: str | None = None) -> T:
    """Fetch by id within the caller's org. Other tenants' rows are indistinguishable from missing ones."""
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "organization_id", None) != user.organization_id:
        raise not_found(what or model.__name__)
    return obj


def allowed_site_ids(user: User) -> list[int] | None:
    """None means all sites in the org (admins). Everyone else sees only assigned sites."""
    return None if Role.admin in user.role_set else user.site_ids


def ensure_site_access(user: User, site_id: int) -> None:
    ids = allowed_site_ids(user)
    if ids is not None and site_id not in ids:
        raise not_found("Site")


# ---- pagination ------------------------------------------------------------------------------


class PageParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> None:
        self.page = page
        self.page_size = page_size


Paging = Annotated[PageParams, Depends()]


def paginate(db: Session, stmt: Select[Any], p: PageParams) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.limit(p.page_size).offset((p.page - 1) * p.page_size)))
    return {"items": items, "total": total, "page": p.page, "page_size": p.page_size}
