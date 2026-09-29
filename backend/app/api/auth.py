import secrets
from typing import Annotated

import pyotp
from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser, ensure_site_access, get_owned, require_roles
from app.core.errors import AppError, bad_request
from app.core.security import hash_secret, limiter, verify_secret
from app.core.time import utcnow
from app.models.org import Area, Device, Organization, RefreshToken, Role, Site, User
from app.schemas.auth import (
    DeviceInfoOut,
    DeviceOperatorOut,
    DeviceRegisterIn,
    DeviceRegisterOut,
    LoginIn,
    MeOut,
    PasswordChangeIn,
    PinChangeIn,
    PinLoginIn,
    SessionOut,
    TokenOut,
    TotpCodeIn,
    TotpSetupOut,
)
from app.schemas.common import Ok
from app.services import audit
from app.services import auth as svc

router = APIRouter(tags=["auth"])

REFRESH_COOKIE = "fp_refresh"
CSRF_COOKIE = "fp_csrf"
REFRESH_PATH = "/api/v1/auth"


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def me_out(db: Session, user: User) -> MeOut:
    org = db.get(Organization, user.organization_id)
    return MeOut(
        id=user.id,
        organization_id=user.organization_id,
        name=user.name,
        email=user.email,
        employee_code=user.employee_code,
        roles=sorted(user.role_set),
        site_ids=sorted(user.site_ids),
        language=user.language,
        totp_enabled=user.totp_enabled,
        organization_name=org.name if org else "",
    )


def _set_session_cookies(response: Response, refresh_token: str) -> None:
    s = get_settings()
    max_age = s.refresh_token_days * 86400
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path=REFRESH_PATH,
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(24),
        max_age=max_age,
        httponly=False,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def _check_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise AppError(403, "csrf_failed", "CSRF check failed")


def _token_out(db: Session, response: Response, t: svc.IssuedTokens) -> TokenOut:
    _set_session_cookies(response, t.refresh_token)
    return TokenOut(
        access_token=t.access_token,
        expires_in=get_settings().access_token_minutes * 60,
        user=me_out(db, t.user),
    )


@router.post("/auth/login", response_model=TokenOut)
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: DB,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenOut:
    limiter.check(f"login:{_ip(request)}", 20, 60)
    limiter.check(f"login:{body.email.lower()}", 10, 300)
    t = svc.password_login(
        db, body.email, body.password, body.totp_code, user_agent=user_agent, ip=_ip(request)
    )
    return _token_out(db, response, t)


@router.get("/auth/device", response_model=DeviceInfoOut)
def device_info(
    db: DB, request: Request, x_device_token: Annotated[str | None, Header()] = None
) -> DeviceInfoOut:
    """Operator picker for a registered shop-floor device."""
    limiter.check(f"device:{_ip(request)}", 60, 60)
    device = svc.device_from_token(db, x_device_token)
    site = db.get(Site, device.site_id)
    org = db.get(Organization, device.organization_id)
    users = db.scalars(
        select(User)
        .where(
            User.organization_id == device.organization_id,
            User.is_active.is_(True),
            User.pin_hash.is_not(None),
        )
        .order_by(User.name)
    ).all()
    operators = [DeviceOperatorOut.model_validate(u) for u in users if device.site_id in u.site_ids]
    return DeviceInfoOut(
        id=device.id,
        name=device.name,
        site_id=device.site_id,
        site_name=site.name if site else "",
        area_id=device.area_id,
        organization_name=org.name if org else "",
        operators=operators,
    )


@router.post("/auth/pin-login", response_model=TokenOut)
def pin_login(
    body: PinLoginIn,
    request: Request,
    response: Response,
    db: DB,
    x_device_token: Annotated[str | None, Header()] = None,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenOut:
    limiter.check(f"pin:{_ip(request)}", 30, 60)
    device = svc.device_from_token(db, x_device_token)
    t = svc.pin_login(db, device, body.user_id, body.pin, user_agent=user_agent, ip=_ip(request))
    return _token_out(db, response, t)


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    db: DB,
    fp_refresh: Annotated[str | None, Cookie()] = None,
    fp_csrf: Annotated[str | None, Cookie()] = None,
    x_csrf_token: Annotated[str | None, Header()] = None,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenOut:
    limiter.check(f"refresh:{_ip(request)}", 60, 60)
    _check_csrf(fp_csrf, x_csrf_token)
    try:
        t = svc.refresh(db, fp_refresh, user_agent=user_agent, ip=_ip(request))
    except AppError:
        _clear_session_cookies(response)
        raise
    return _token_out(db, response, t)


@router.post("/auth/logout", response_model=Ok)
def logout(
    response: Response,
    db: DB,
    fp_refresh: Annotated[str | None, Cookie()] = None,
    fp_csrf: Annotated[str | None, Cookie()] = None,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> Ok:
    _check_csrf(fp_csrf, x_csrf_token)
    family = svc.family_of(db, fp_refresh)
    if family:
        svc.revoke_family(db, family)
        db.commit()
    _clear_session_cookies(response)
    return Ok()


# ---- me --------------------------------------------------------------------------------------


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: DB) -> MeOut:
    return me_out(db, user)


@router.get("/me/sessions", response_model=list[SessionOut])
def my_sessions(user: CurrentUser, db: DB, request: Request) -> list[SessionOut]:
    now = utcnow()
    rows = db.scalars(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.used_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.desc())
    ).all()
    current = getattr(request.state, "session_id", None)
    firsts = {}
    for fam in {r.family_id for r in rows}:
        firsts[fam] = db.scalar(
            select(RefreshToken.created_at)
            .where(RefreshToken.family_id == fam)
            .order_by(RefreshToken.created_at)
            .limit(1)
        )
    return [
        SessionOut(
            id=r.family_id,
            auth_method=r.auth_method,
            user_agent=r.user_agent,
            ip=r.ip,
            created_at=firsts.get(r.family_id) or r.created_at,
            last_used_at=r.created_at,
            current=r.family_id == current,
        )
        for r in rows
    ]


@router.delete("/me/sessions/{family_id}", response_model=Ok)
def revoke_session(family_id: str, user: CurrentUser, db: DB) -> Ok:
    owned = db.scalar(
        select(RefreshToken.id)
        .where(RefreshToken.family_id == family_id, RefreshToken.user_id == user.id)
        .limit(1)
    )
    if owned is None:
        raise AppError(404, "not_found", "Session not found")
    svc.revoke_family(db, family_id)
    audit.record(db, user, "auth.session_revoked", "user", user.id)
    db.commit()
    return Ok()


@router.post("/me/pin", response_model=Ok)
def change_pin(body: PinChangeIn, user: CurrentUser, db: DB) -> Ok:
    user.set_pin(body.pin)
    audit.record(db, user, "user.pin_changed", "user", user.id)
    db.commit()
    return Ok()


@router.post("/me/password", response_model=Ok)
def change_password(body: PasswordChangeIn, user: CurrentUser, db: DB, request: Request) -> Ok:
    limiter.check(f"pwchange:{user.id}", 5, 300)
    if not verify_secret(user.password_hash, body.current_password):
        raise bad_request("wrong_password", "Current password is wrong")
    user.password_hash = hash_secret(body.new_password)
    audit.record(db, user, "user.password_changed", "user", user.id)
    db.commit()
    return Ok()


@router.post("/me/totp/setup", response_model=TotpSetupOut)
def totp_setup(user: CurrentUser, db: DB) -> TotpSetupOut:
    if user.totp_enabled:
        raise bad_request("totp_already_enabled", "Two-factor authentication is already on")
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email or user.name, issuer_name="FloorPulse")
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/me/totp/enable", response_model=Ok)
def totp_enable(body: TotpCodeIn, user: CurrentUser, db: DB) -> Ok:
    if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise bad_request("totp_invalid", "Wrong authenticator code")
    user.totp_enabled = True
    audit.record(db, user, "user.totp_enabled", "user", user.id)
    db.commit()
    return Ok()


@router.post("/me/totp/disable", response_model=Ok)
def totp_disable(body: TotpCodeIn, user: CurrentUser, db: DB) -> Ok:
    if not user.totp_enabled or not pyotp.TOTP(user.totp_secret or "").verify(body.code, valid_window=1):
        raise bad_request("totp_invalid", "Wrong authenticator code")
    user.totp_enabled = False
    user.totp_secret = None
    audit.record(db, user, "user.totp_disabled", "user", user.id)
    db.commit()
    return Ok()


# ---- devices ---------------------------------------------------------------------------------

_supervisor = Depends(require_roles(Role.supervisor, Role.manager))


@router.post("/devices", response_model=DeviceRegisterOut, status_code=201)
def register_device(body: DeviceRegisterIn, db: DB, user: User = _supervisor) -> DeviceRegisterOut:
    site = get_owned(db, Site, body.site_id, user, "Site")
    ensure_site_access(user, site.id)
    if body.area_id is not None:
        area = get_owned(db, Area, body.area_id, user, "Line")
        if area.site_id != site.id:
            raise bad_request("area_site_mismatch", "Line does not belong to that site")
    device, raw = svc.register_device(db, user, body.name, site.id, body.area_id)
    return DeviceRegisterOut(id=device.id, device_token=raw, site_id=device.site_id, area_id=device.area_id)


@router.delete("/devices/{device_id}", response_model=Ok)
def revoke_device(device_id: int, db: DB, user: User = _supervisor) -> Ok:
    device = get_owned(db, Device, device_id, user, "Device")
    device.revoked_at = utcnow()
    audit.record(db, user, "device.revoke", "device", device.id)
    db.commit()
    return Ok()
