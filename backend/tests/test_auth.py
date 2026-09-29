from datetime import timedelta

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.audit import AuditLog
from app.models.org import RefreshToken, Role
from tests.factories import PASSWORD, PIN, Tenant


def _login(client: TestClient, email: str, password: str = PASSWORD, **extra: str) -> dict:  # type: ignore[type-arg]
    return client.post("/api/v1/auth/login", json={"email": email, "password": password, **extra})  # type: ignore[return-value]


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("fp_csrf") or ""}


def test_login_every_role(client: TestClient, tenant: Tenant) -> None:
    for role in Role:
        r = _login(client, f"{role.value}@acme.test")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["roles"] == [role.value]
        me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.json()["email"] == f"{role.value}@acme.test"


def test_login_wrong_password_uses_envelope(client: TestClient, tenant: Tenant) -> None:
    r = _login(client, "admin@acme.test", "nope")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_login_is_rate_limited(client: TestClient, tenant: Tenant) -> None:
    codes = [_login(client, "admin@acme.test", "nope").status_code for _ in range(12)]
    assert codes[-1] == 429


def test_refresh_rotates_and_detects_reuse(client: TestClient, tenant: Tenant, db: Session) -> None:
    assert _login(client, "manager@acme.test").status_code == 200
    first = client.cookies.get("fp_refresh")
    r = client.post("/api/v1/auth/refresh", headers=_csrf(client))
    assert r.status_code == 200
    second = client.cookies.get("fp_refresh")
    assert second and second != first

    # Replaying the old token outside the race window revokes the whole family.
    old = db.scalar(select(RefreshToken).where(RefreshToken.used_at.is_not(None)))
    assert old is not None
    old.used_at = utcnow() - timedelta(minutes=1)
    db.commit()
    client.cookies.set("fp_refresh", first or "", path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=_csrf(client)).status_code == 401
    client.cookies.set("fp_refresh", second, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=_csrf(client)).status_code == 401


def test_refresh_requires_csrf(client: TestClient, tenant: Tenant) -> None:
    _login(client, "manager@acme.test")
    r = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "wrong"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


def test_logout_revokes_session(client: TestClient, tenant: Tenant) -> None:
    _login(client, "manager@acme.test")
    token = client.cookies.get("fp_refresh")
    assert client.post("/api/v1/auth/logout", headers=_csrf(client)).status_code == 200
    client.cookies.set("fp_refresh", token or "", path="/api/v1/auth")
    client.cookies.set("fp_csrf", "x")
    assert client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "x"}).status_code == 401


def _register_device(client: TestClient, tenant: Tenant) -> str:
    r = client.post(
        "/api/v1/devices",
        headers=tenant.headers(Role.supervisor),
        json={"name": "Line 1 tablet", "site_id": tenant.site.id, "area_id": tenant.area.id},
    )
    assert r.status_code == 201, r.text
    return r.json()["device_token"]  # type: ignore[no-any-return]


def test_pin_login_flow(client: TestClient, tenant: Tenant) -> None:
    dev = _register_device(client, tenant)
    info = client.get("/api/v1/auth/device", headers={"X-Device-Token": dev})
    assert info.status_code == 200
    op = tenant.users[Role.operator]
    assert op.id in [o["id"] for o in info.json()["operators"]]
    r = client.post(
        "/api/v1/auth/pin-login", headers={"X-Device-Token": dev}, json={"user_id": op.id, "pin": PIN}
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["roles"] == ["operator"]


def test_pin_login_needs_registered_device(client: TestClient, tenant: Tenant) -> None:
    op = tenant.users[Role.operator]
    r = client.post(
        "/api/v1/auth/pin-login", headers={"X-Device-Token": "bogus"}, json={"user_id": op.id, "pin": PIN}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "device_required"


def test_pin_lockout(client: TestClient, tenant: Tenant) -> None:
    dev = _register_device(client, tenant)
    op = tenant.users[Role.operator]
    h = {"X-Device-Token": dev}
    for _ in range(5):
        assert (
            client.post(
                "/api/v1/auth/pin-login", headers=h, json={"user_id": op.id, "pin": "9999"}
            ).status_code
            == 401
        )
    r = client.post("/api/v1/auth/pin-login", headers=h, json={"user_id": op.id, "pin": PIN})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "pin_locked"


def test_pin_login_cannot_cross_tenant(client: TestClient, tenant: Tenant, other_tenant: Tenant) -> None:
    dev = _register_device(client, tenant)
    rival_op = other_tenant.users[Role.operator]
    r = client.post(
        "/api/v1/auth/pin-login", headers={"X-Device-Token": dev}, json={"user_id": rival_op.id, "pin": PIN}
    )
    assert r.status_code == 401


def test_revoked_device_blocks_refresh(client: TestClient, tenant: Tenant) -> None:
    r = client.post(
        "/api/v1/devices",
        headers=tenant.headers(Role.supervisor),
        json={"name": "tab", "site_id": tenant.site.id},
    )
    dev, dev_id = r.json()["device_token"], r.json()["id"]
    op = tenant.users[Role.operator]
    client.post(
        "/api/v1/auth/pin-login", headers={"X-Device-Token": dev}, json={"user_id": op.id, "pin": PIN}
    )
    client.delete(f"/api/v1/devices/{dev_id}", headers=tenant.headers(Role.supervisor))
    assert client.post("/api/v1/auth/refresh", headers=_csrf(client)).status_code == 401


def test_totp_enrolment_and_login(client: TestClient, tenant: Tenant) -> None:
    h = tenant.headers(Role.manager)
    secret = client.post("/api/v1/me/totp/setup", headers=h).json()["secret"]
    assert (
        client.post("/api/v1/me/totp/enable", headers=h, json={"code": pyotp.TOTP(secret).now()}).status_code
        == 200
    )
    r = _login(client, "manager@acme.test")
    assert r.json()["error"]["code"] == "totp_required"
    r = _login(client, "manager@acme.test", totp_code="000000")
    assert r.json()["error"]["code"] == "totp_invalid"
    r = _login(client, "manager@acme.test", totp_code=pyotp.TOTP(secret).now())
    assert r.status_code == 200


def test_sessions_list_and_remote_logout(client: TestClient, tenant: Tenant) -> None:
    access = _login(client, "manager@acme.test").json()["access_token"]
    h = {"Authorization": f"Bearer {access}"}
    sessions = client.get("/api/v1/me/sessions", headers=h).json()
    assert len(sessions) == 1 and sessions[0]["current"]
    assert client.delete(f"/api/v1/me/sessions/{sessions[0]['id']}", headers=h).status_code == 200
    assert client.post("/api/v1/auth/refresh", headers=_csrf(client)).status_code == 401


def test_deactivated_user_loses_access(client: TestClient, tenant: Tenant) -> None:
    op = tenant.users[Role.operator]
    h_op = tenant.headers(Role.operator)
    assert client.get("/api/v1/me", headers=h_op).status_code == 200
    r = client.patch(f"/api/v1/users/{op.id}", headers=tenant.headers(), json={"is_active": False})
    assert r.status_code == 200
    assert client.get("/api/v1/me", headers=h_op).status_code == 401


def test_login_is_audited(client: TestClient, tenant: Tenant, db: Session) -> None:
    _login(client, "admin@acme.test")
    n = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "auth.login"))
    assert n == 1


def test_expired_token_rejected(client: TestClient, tenant: Tenant) -> None:
    import jwt

    from app.core.config import get_settings

    u = tenant.users[Role.admin]
    token = jwt.encode(
        {"sub": str(u.id), "org": u.organization_id, "typ": "access", "exp": 1},
        get_settings().secret_key,
        algorithm="HS256",
    )
    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "token_expired"
