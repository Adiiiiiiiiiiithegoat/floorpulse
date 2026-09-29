"""Authentication: password/PIN login, refresh-token rotation with reuse detection, devices, TOTP."""

import secrets
from dataclasses import dataclass
from datetime import timedelta

import pyotp
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, new_opaque_token, sha256, verify_secret
from app.core.time import utcnow
from app.models.org import Device, Organization, RefreshToken, Role, User
from app.schemas.settings import load_settings
from app.services import audit

_BAD_LOGIN = AppError(401, "invalid_credentials", "Wrong email or password")


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    user: User


def _issue(
    db: Session,
    user: User,
    *,
    family_id: str | None = None,
    method: str = "password",
    device_id: int | None = None,
    user_agent: str | None = None,
    ip: str | None = None,
) -> IssuedTokens:
    s = get_settings()
    now = utcnow()
    raw = new_opaque_token()
    family_id = family_id or secrets.token_hex(16)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=sha256(raw),
            family_id=family_id,
            device_id=device_id,
            auth_method=method,
            user_agent=(user_agent or "")[:300] or None,
            ip=ip,
            created_at=now,
            expires_at=now + timedelta(days=s.refresh_token_days),
        )
    )
    access = create_access_token(user.id, user.organization_id, sorted(user.role_set), device_id, family_id)
    return IssuedTokens(access, raw, user)


def password_login(
    db: Session, email: str, password: str, totp_code: str | None, *, user_agent: str | None, ip: str | None
) -> IssuedTokens:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_secret(user.password_hash, password) or not user.is_active:
        raise _BAD_LOGIN
    org = db.get(Organization, user.organization_id)
    needs_2fa = user.totp_enabled or (
        org is not None
        and load_settings(org.settings).require_2fa_for_admins
        and user.role_set & {Role.admin, Role.manager}
    )
    if needs_2fa:
        if not user.totp_enabled:
            raise AppError(403, "totp_setup_required", "Two-factor authentication must be set up first")
        if not totp_code:
            raise AppError(401, "totp_required", "Enter the 6-digit code from your authenticator app")
        if not pyotp.TOTP(user.totp_secret or "").verify(totp_code, valid_window=1):
            raise AppError(401, "totp_invalid", "Wrong authenticator code")
    user.last_login_at = utcnow()
    audit.record(db, user, "auth.login", "user", user.id, note="password")
    tokens = _issue(db, user, method="password", user_agent=user_agent, ip=ip)
    db.commit()
    return tokens


def device_from_token(db: Session, raw: str | None) -> Device:
    if not raw:
        raise AppError(401, "device_required", "This device is not registered")
    device = db.scalar(select(Device).where(Device.token_hash == sha256(raw)))
    if device is None or device.revoked_at is not None:
        raise AppError(401, "device_required", "This device is not registered")
    return device


def pin_login(
    db: Session, device: Device, user_id: int, pin: str, *, user_agent: str | None, ip: str | None
) -> IssuedTokens:
    s = get_settings()
    now = utcnow()
    user = db.get(User, user_id)
    if (
        user is None
        or user.organization_id != device.organization_id
        or not user.is_active
        or device.site_id not in user.site_ids
    ):
        raise AppError(401, "invalid_credentials", "Wrong PIN")
    if user.locked_until and user.locked_until > now:
        raise AppError(
            429,
            "pin_locked",
            "Too many wrong PINs. Ask your supervisor or wait a few minutes.",
            {"locked_until": user.locked_until.isoformat()},
        )
    if not verify_secret(user.pin_hash, pin):
        user.failed_pin_attempts += 1
        if user.failed_pin_attempts >= s.pin_max_failures:
            user.locked_until = now + timedelta(minutes=s.pin_lockout_minutes)
            user.failed_pin_attempts = 0
            audit.record(db, None, "auth.pin_locked", "user", user.id, org_id=user.organization_id)
        db.commit()
        raise AppError(401, "invalid_credentials", "Wrong PIN")
    user.failed_pin_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    device.last_seen_at = now
    audit.record(db, user, "auth.login", "user", user.id, note=f"pin device={device.id}")
    tokens = _issue(db, user, method="pin", device_id=device.id, user_agent=user_agent, ip=ip)
    db.commit()
    return tokens


def refresh(db: Session, raw: str | None, *, user_agent: str | None, ip: str | None) -> IssuedTokens:
    bad = AppError(401, "invalid_refresh", "Session expired, please log in again")
    if not raw:
        raise bad
    now = utcnow()
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha256(raw)))
    if row is None:
        raise bad
    if row.used_at is not None or row.revoked_at is not None:
        # Reuse of a rotated token: assume theft and kill the session family. A reuse within a few
        # seconds is almost always two tabs racing, so it is rejected without revoking.
        if row.used_at is not None and row.revoked_at is None and now - row.used_at > timedelta(seconds=15):
            revoke_family(db, row.family_id)
            user = db.get(User, row.user_id)
            if user:
                audit.record(db, user, "auth.refresh_reuse", "user", user.id, note="session revoked")
            db.commit()
        raise bad
    if row.expires_at <= now:
        raise bad
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise bad
    if row.device_id is not None:
        device = db.get(Device, row.device_id)
        if device is None or device.revoked_at is not None:
            raise bad
    row.used_at = now
    tokens = _issue(
        db,
        user,
        family_id=row.family_id,
        method=row.auth_method,
        device_id=row.device_id,
        user_agent=user_agent,
        ip=ip,
    )
    db.commit()
    return tokens


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def family_of(db: Session, raw: str | None) -> str | None:
    if not raw:
        return None
    return db.scalar(select(RefreshToken.family_id).where(RefreshToken.token_hash == sha256(raw)))


def register_device(
    db: Session, actor: User, name: str, site_id: int, area_id: int | None
) -> tuple[Device, str]:
    raw = new_opaque_token()
    device = Device(
        organization_id=actor.organization_id,
        created_by=actor.id,
        name=name,
        token_hash=sha256(raw),
        site_id=site_id,
        area_id=area_id,
    )
    db.add(device)
    db.flush()
    audit.record(db, actor, "device.register", "device", device.id, after={"name": name, "site_id": site_id})
    db.commit()
    return device, raw
