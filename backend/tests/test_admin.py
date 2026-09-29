from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.org import Role
from tests.factories import Tenant


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
    r = client.get("/healthz")
    assert "X-Request-ID" in r.headers and r.headers["X-Content-Type-Options"] == "nosniff"
    assert "fp_http_requests_total" in client.get("/metrics").text


def test_create_user_and_audit(client: TestClient, tenant: Tenant, db: Session) -> None:
    r = client.post(
        "/api/v1/users",
        headers=tenant.headers(),
        json={
            "name": "Ravi",
            "employee_code": "E100",
            "pin": "4321",
            "roles": ["operator"],
            "site_ids": [tenant.site.id],
        },
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert r.json()["has_pin"] and not r.json()["has_password"]
    row = db.scalar(select(AuditLog).where(AuditLog.action == "user.create", AuditLog.entity_id == str(uid)))
    assert row is not None and row.after is not None
    assert row.after["pin_hash"] == "***"  # secrets never land in the audit log


def test_update_site_records_before_after(client: TestClient, tenant: Tenant, db: Session) -> None:
    r = client.patch(f"/api/v1/sites/{tenant.site.id}", headers=tenant.headers(), json={"name": "Renamed"})
    assert r.status_code == 200
    row = db.scalar(select(AuditLog).where(AuditLog.action == "site.update"))
    assert row is not None
    assert row.before == {"name": "acme plant"} and row.after == {"name": "Renamed"}


def test_etag_prevents_lost_update(client: TestClient, tenant: Tenant) -> None:
    h = tenant.headers()
    etag = client.get(f"/api/v1/sites/{tenant.site.id}", headers=h).headers["ETag"]
    assert (
        client.patch(
            f"/api/v1/sites/{tenant.site.id}", headers={**h, "If-Match": etag}, json={"name": "A"}
        ).status_code
        == 200
    )
    r = client.patch(f"/api/v1/sites/{tenant.site.id}", headers={**h, "If-Match": etag}, json={"name": "B"})
    assert r.status_code == 412
    assert r.json()["error"]["code"] == "stale_record"


def test_duplicate_site_code_is_409(client: TestClient, tenant: Tenant) -> None:
    r = client.post("/api/v1/sites", headers=tenant.headers(), json={"name": "dup", "code": "P1"})
    assert r.status_code == 409


def test_invalid_timezone_rejected(client: TestClient, tenant: Tenant) -> None:
    r = client.post(
        "/api/v1/sites", headers=tenant.headers(), json={"name": "x", "code": "X", "timezone": "Mars/Base"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_admin_cannot_lock_self_out(client: TestClient, tenant: Tenant) -> None:
    me = tenant.users[Role.admin]
    r = client.patch(f"/api/v1/users/{me.id}", headers=tenant.headers(), json={"is_active": False})
    assert r.status_code == 400


def test_archive_site_hides_it(client: TestClient, tenant: Tenant) -> None:
    h = tenant.headers()
    client.patch(f"/api/v1/sites/{tenant.site.id}", headers=h, json={"archived": True})
    assert client.get("/api/v1/sites", headers=h).json() == []
    assert len(client.get("/api/v1/sites?include_archived=true", headers=h).json()) == 1


def test_non_admin_sees_only_assigned_sites(client: TestClient, tenant: Tenant) -> None:
    client.post("/api/v1/sites", headers=tenant.headers(), json={"name": "Second", "code": "P2"})
    assert len(client.get("/api/v1/sites", headers=tenant.headers()).json()) == 2
    assert len(client.get("/api/v1/sites", headers=tenant.headers(Role.manager)).json()) == 1


def test_org_settings_roundtrip(client: TestClient, tenant: Tenant) -> None:
    h = tenant.headers()
    s = client.get("/api/v1/org/settings", headers=h).json()
    assert s["currency"] == "INR" and s["show_operator_analytics"] is False
    s["currency"] = "USD"
    assert client.put("/api/v1/org/settings", headers=h, json=s).json()["currency"] == "USD"


def test_body_size_limit(client: TestClient, tenant: Tenant) -> None:
    r = client.post(
        "/api/v1/sites", headers={**tenant.headers(), "Content-Length": str(50 * 1024 * 1024)}, content=b"{}"
    )
    assert r.status_code == 413
