from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import (
    DB,
    CurrentUser,
    Paging,
    allowed_site_ids,
    ensure_site_access,
    get_owned,
    paginate,
    require_roles,
    scoped,
)
from app.core.errors import bad_request
from app.core.etag import check_if_match, set_etag
from app.core.security import hash_secret
from app.core.time import utcnow
from app.models.audit import AuditLog
from app.models.org import Area, Organization, Role, Site, User, UserRole, UserSite
from app.schemas.common import Page
from app.schemas.org import (
    AreaIn,
    AreaOut,
    AreaPatch,
    AuditOut,
    SiteIn,
    SiteOut,
    SitePatch,
    UserIn,
    UserOut,
    UserPatch,
)
from app.schemas.settings import OrgSettings, load_settings
from app.services import audit
from app.services import auth as auth_svc

router = APIRouter(tags=["admin"])
Admin = Annotated[User, Depends(require_roles())]  # admin only
IfMatch = Annotated[str | None, Header()]


def _apply(obj: Any, patch: dict[str, Any]) -> None:
    for k, v in patch.items():
        setattr(obj, k, v)


def _archive(obj: Any, archived: bool | None) -> None:
    if archived is True and obj.archived_at is None:
        obj.archived_at = utcnow()
    elif archived is False:
        obj.archived_at = None


# ---- org settings ----------------------------------------------------------------------------


@router.get("/org/settings", response_model=OrgSettings)
def get_org_settings(user: CurrentUser, db: DB) -> OrgSettings:
    org = db.get(Organization, user.organization_id)
    return load_settings(org.settings if org else None)


@router.put("/org/settings", response_model=OrgSettings)
def put_org_settings(body: OrgSettings, user: Admin, db: DB) -> OrgSettings:
    org = db.get(Organization, user.organization_id)
    assert org is not None
    before = org.settings
    org.settings = body.model_dump(mode="json")
    audit.record(db, user, "org.settings_updated", "organization", org.id, before=before, after=org.settings)
    db.commit()
    return body


# ---- sites -----------------------------------------------------------------------------------


@router.get("/sites", response_model=list[SiteOut])
def list_sites(user: CurrentUser, db: DB, include_archived: bool = False) -> list[Site]:
    stmt = scoped(select(Site), Site, user).order_by(Site.name)
    if not include_archived:
        stmt = stmt.where(Site.archived_at.is_(None))
    ids = allowed_site_ids(user)
    if ids is not None:
        stmt = stmt.where(Site.id.in_(ids))
    return list(db.scalars(stmt))


@router.post("/sites", response_model=SiteOut, status_code=201)
def create_site(body: SiteIn, user: Admin, db: DB) -> Site:
    site = Site(organization_id=user.organization_id, created_by=user.id, **body.model_dump())
    db.add(site)
    db.flush()
    audit.record(db, user, "site.create", "site", site.id, after=audit.snapshot(site))
    db.commit()
    return site


@router.get("/sites/{site_id}", response_model=SiteOut)
def get_site(site_id: int, user: CurrentUser, db: DB, response: Response) -> Site:
    site = get_owned(db, Site, site_id, user, "Site")
    ensure_site_access(user, site.id)
    set_etag(response, site.id, site.updated_at)
    return site


@router.patch("/sites/{site_id}", response_model=SiteOut)
def patch_site(
    site_id: int, body: SitePatch, user: Admin, db: DB, response: Response, if_match: IfMatch = None
) -> Site:
    site = get_owned(db, Site, site_id, user, "Site")
    check_if_match(if_match, site.id, site.updated_at)
    before = audit.snapshot(site)
    data = body.model_dump(exclude_unset=True)
    _archive(site, data.pop("archived", None))
    _apply(site, data)
    db.flush()
    b, a = audit.diff(before, audit.snapshot(site))
    audit.record(db, user, "site.update", "site", site.id, before=b, after=a)
    db.commit()
    set_etag(response, site.id, site.updated_at)
    return site


# ---- areas (lines) ---------------------------------------------------------------------------


@router.get("/areas", response_model=list[AreaOut])
def list_areas(
    user: CurrentUser, db: DB, site_id: int | None = None, include_archived: bool = False
) -> list[Area]:
    stmt = scoped(select(Area), Area, user).order_by(Area.name)
    if site_id is not None:
        stmt = stmt.where(Area.site_id == site_id)
    if not include_archived:
        stmt = stmt.where(Area.archived_at.is_(None))
    ids = allowed_site_ids(user)
    if ids is not None:
        stmt = stmt.where(Area.site_id.in_(ids))
    return list(db.scalars(stmt))


@router.post("/areas", response_model=AreaOut, status_code=201)
def create_area(body: AreaIn, user: Admin, db: DB) -> Area:
    get_owned(db, Site, body.site_id, user, "Site")
    area = Area(organization_id=user.organization_id, created_by=user.id, **body.model_dump())
    db.add(area)
    db.flush()
    audit.record(db, user, "area.create", "area", area.id, after=audit.snapshot(area))
    db.commit()
    return area


@router.patch("/areas/{area_id}", response_model=AreaOut)
def patch_area(
    area_id: int, body: AreaPatch, user: Admin, db: DB, response: Response, if_match: IfMatch = None
) -> Area:
    area = get_owned(db, Area, area_id, user, "Line")
    check_if_match(if_match, area.id, area.updated_at)
    before = audit.snapshot(area)
    data = body.model_dump(exclude_unset=True)
    _archive(area, data.pop("archived", None))
    _apply(area, data)
    db.flush()
    b, a = audit.diff(before, audit.snapshot(area))
    audit.record(db, user, "area.update", "area", area.id, before=b, after=a)
    db.commit()
    set_etag(response, area.id, area.updated_at)
    return area


# ---- users -----------------------------------------------------------------------------------


def user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        name=u.name,
        email=u.email,
        employee_code=u.employee_code,
        phone=u.phone,
        roles=sorted(u.role_set),
        site_ids=sorted(u.site_ids),
        language=u.language,
        is_active=u.is_active,
        has_pin=u.pin_hash is not None,
        has_password=u.password_hash is not None,
        totp_enabled=u.totp_enabled,
        last_login_at=u.last_login_at,
        updated_at=u.updated_at,
    )


def _user_state(u: User) -> dict[str, Any]:
    snap = audit.snapshot(u)
    snap["roles"] = sorted(u.role_set)
    snap["site_ids"] = sorted(u.site_ids)
    return snap


def _check_sites(db: Session, user: User, site_ids: list[int]) -> None:
    for sid in site_ids:
        get_owned(db, Site, sid, user, "Site")


@router.get("/users", response_model=Page[UserOut])
def list_users(
    user: Annotated[User, Depends(require_roles(Role.manager, Role.supervisor))],
    db: DB,
    paging: Paging,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Role | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    stmt = scoped(select(User), User, user).order_by(User.name)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(User.name.ilike(like) | User.email.ilike(like) | User.employee_code.ilike(like))
    if role:
        stmt = stmt.where(User.id.in_(select(UserRole.user_id).where(UserRole.role == role.value)))
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    page = paginate(db, stmt, paging)
    page["items"] = [user_out(u) for u in page["items"]]
    return page


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, user: Admin, db: DB) -> UserOut:
    _check_sites(db, user, body.site_ids)
    if not body.password and not body.pin:
        raise bad_request("credential_required", "Give the user a password or a PIN")
    u = User(
        organization_id=user.organization_id,
        name=body.name,
        email=body.email.lower() if body.email else None,
        employee_code=body.employee_code,
        phone=body.phone,
        language=body.language,
        password_hash=hash_secret(body.password) if body.password else None,
        roles=[UserRole(role=r.value) for r in set(body.roles)],
        sites=[UserSite(site_id=s) for s in set(body.site_ids)],
    )
    if body.pin:
        u.set_pin(body.pin)
    db.add(u)
    db.flush()
    audit.record(db, user, "user.create", "user", u.id, after=_user_state(u))
    db.commit()
    return user_out(u)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, user: Admin, db: DB, response: Response) -> UserOut:
    u = get_owned(db, User, user_id, user, "User")
    set_etag(response, u.id, u.updated_at)
    return user_out(u)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int, body: UserPatch, user: Admin, db: DB, response: Response, if_match: IfMatch = None
) -> UserOut:
    u = get_owned(db, User, user_id, user, "User")
    check_if_match(if_match, u.id, u.updated_at)
    before = _user_state(u)
    data = body.model_dump(exclude_unset=True)
    if u.id == user.id and (
        data.get("is_active") is False or ("roles" in data and Role.admin not in (data["roles"] or []))
    ):
        raise bad_request("self_lockout", "You cannot deactivate yourself or remove your own admin role")
    if (pw := data.pop("password", None)) is not None:
        u.password_hash = hash_secret(pw)
    if (pin := data.pop("pin", None)) is not None:
        u.set_pin(pin)
    if (roles := data.pop("roles", None)) is not None:
        u.roles = [UserRole(role=r.value) for r in set(roles)]
    if (sites := data.pop("site_ids", None)) is not None:
        _check_sites(db, user, sites)
        u.sites = [UserSite(site_id=s) for s in set(sites)]
    if data.get("email"):
        data["email"] = data["email"].lower()
    if (active := data.pop("is_active", None)) is not None and active != u.is_active:
        u.is_active = active
        u.deactivated_at = None if active else utcnow()
        if not active:
            auth_svc.revoke_all_for_user(db, u.id)
    _apply(u, data)
    u.updated_at = utcnow()  # role/site changes live in child tables
    db.flush()
    b, a = audit.diff(before, _user_state(u))
    audit.record(db, user, "user.update", "user", u.id, before=b, after=a)
    db.commit()
    set_etag(response, u.id, u.updated_at)
    return user_out(u)


@router.post("/users/{user_id}/logout-all", response_model=UserOut)
def logout_user_everywhere(user_id: int, user: Admin, db: DB) -> UserOut:
    u = get_owned(db, User, user_id, user, "User")
    auth_svc.revoke_all_for_user(db, u.id)
    audit.record(db, user, "user.sessions_revoked", "user", u.id)
    db.commit()
    return user_out(u)


# ---- audit log -------------------------------------------------------------------------------


@router.get("/audit", response_model=Page[AuditOut])
def list_audit(
    user: Annotated[User, Depends(require_roles(Role.manager))],
    db: DB,
    paging: Paging,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    stmt = scoped(select(AuditLog), AuditLog, user).order_by(AuditLog.id.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until:
        stmt = stmt.where(AuditLog.created_at < until)
    return paginate(db, stmt, paging)
