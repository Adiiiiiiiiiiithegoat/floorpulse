"""Every router must refuse other tenants' rows (404) and under-privileged roles (403).

Add a case to CASES whenever a new endpoint that touches tenant data is added.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.org import Role
from tests.factories import Tenant


@dataclass
class Case:
    method: str
    path: str  # may contain {id}
    make: Callable[[Session, Tenant], int] | None = None  # creates a row in the given tenant, returns its id
    body: dict[str, Any] | Callable[[Tenant], dict[str, Any]] | None = None
    denied: list[Role] = field(default_factory=list)  # roles that must get 403

    def url(self, obj_id: int | None) -> str:
        return self.path.format(id=obj_id)


def _site(db: Session, t: Tenant) -> int:
    return t.site.id


def _area(db: Session, t: Tenant) -> int:
    return t.area.id


def _user(db: Session, t: Tenant) -> int:
    return t.users[Role.operator].id


_NON_ADMIN = [Role.operator, Role.supervisor, Role.technician, Role.inspector, Role.storekeeper, Role.manager]

CASES: list[Case] = [
    Case("GET", "/api/v1/sites/{id}", _site),
    Case("PATCH", "/api/v1/sites/{id}", _site, {"name": "x"}, _NON_ADMIN),
    Case("PATCH", "/api/v1/areas/{id}", _area, {"name": "x"}, _NON_ADMIN),
    Case("GET", "/api/v1/users/{id}", _user, None, _NON_ADMIN),
    Case("PATCH", "/api/v1/users/{id}", _user, {"name": "x"}, _NON_ADMIN),
    Case("POST", "/api/v1/users/{id}/logout-all", _user, None, _NON_ADMIN),
    Case(
        "POST", "/api/v1/areas", None, lambda t: {"site_id": t.site.id, "name": "n", "code": "N"}, _NON_ADMIN
    ),
    Case("POST", "/api/v1/sites", None, {"name": "n", "code": "N"}, _NON_ADMIN),
    Case("PUT", "/api/v1/org/settings", None, {}, _NON_ADMIN),
    Case(
        "GET", "/api/v1/users", None, None, [Role.operator, Role.technician, Role.inspector, Role.storekeeper]
    ),
    Case("GET", "/api/v1/audit", None, None, [Role.operator, Role.supervisor, Role.technician]),
    Case("POST", "/api/v1/devices", None, lambda t: {"name": "d", "site_id": t.site.id}, [Role.operator]),
]


def _body(case: Case, t: Tenant) -> dict[str, Any] | None:
    return case.body(t) if callable(case.body) else case.body


@pytest.mark.parametrize("case", [c for c in CASES if c.make], ids=lambda c: f"{c.method} {c.path}")
def test_wrong_tenant_gets_404(
    case: Case, client: TestClient, db: Session, tenant: Tenant, other_tenant: Tenant
) -> None:
    foreign_id = case.make(db, other_tenant)  # type: ignore[misc]
    r = client.request(
        case.method, case.url(foreign_id), headers=tenant.headers(Role.admin), json=_body(case, tenant)
    )
    assert r.status_code == 404, r.text


@pytest.mark.parametrize("case", [c for c in CASES if c.denied], ids=lambda c: f"{c.method} {c.path}")
def test_wrong_role_gets_403(case: Case, client: TestClient, db: Session, tenant: Tenant) -> None:
    obj_id = case.make(db, tenant) if case.make else None
    for role in case.denied:
        r = client.request(
            case.method, case.url(obj_id), headers=tenant.headers(role), json=_body(case, tenant)
        )
        assert r.status_code == 403, f"{role}: {r.status_code} {r.text}"


def test_lists_only_show_own_tenant(client: TestClient, tenant: Tenant, other_tenant: Tenant) -> None:
    h = tenant.headers(Role.admin)
    sites = client.get("/api/v1/sites", headers=h).json()
    assert [s["id"] for s in sites] == [tenant.site.id]
    users = client.get("/api/v1/users", headers=h).json()["items"]
    assert {u["id"] for u in users} == {u.id for u in tenant.users.values()}
    areas = client.get("/api/v1/areas", headers=h).json()
    assert [a["id"] for a in areas] == [tenant.area.id]


def test_cannot_assign_foreign_site_to_user(client: TestClient, tenant: Tenant, other_tenant: Tenant) -> None:
    r = client.post(
        "/api/v1/users",
        headers=tenant.headers(),
        json={"name": "Spy", "pin": "1234", "roles": ["operator"], "site_ids": [other_tenant.site.id]},
    )
    assert r.status_code == 404


def test_unauthenticated_gets_401(client: TestClient) -> None:
    r = client.get("/api/v1/sites")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
