"""Deterministic demo organization. Later phases extend `seed()` with operational history."""

import random
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.security import hash_secret, sha256
from app.models.org import Area, Device, Organization, Role, Site, User, UserRole, UserSite
from app.services import audit

DEMO_PASSWORD = "FloorPulse!2026"
DEMO_PIN = "1234"
DEMO_ORG = "Demo Auto Components Pvt Ltd"

SITES = [
    (
        "Pune Plant",
        "PUN",
        "Asia/Kolkata",
        [("Machining Line", "MCH"), ("Press Shop", "PRS"), ("Assembly Line", "ASM")],
    ),
    (
        "Chennai Plant",
        "CHE",
        "Asia/Kolkata",
        [("Moulding Line", "MLD"), ("CNC Cell", "CNC"), ("Packing Line", "PKG")],
    ),
]

# (name, email, employee code, roles, site codes)
USERS: list[tuple[str, str | None, str, list[Role], list[str]]] = [
    ("Anita Desai", "admin@demo.floorpulse.app", "E001", [Role.admin], ["PUN", "CHE"]),
    ("Rajesh Kumar", "manager@demo.floorpulse.app", "E002", [Role.manager], ["PUN", "CHE"]),
    ("Suresh Patil", "supervisor.pune@demo.floorpulse.app", "E003", [Role.supervisor], ["PUN"]),
    ("Meena Iyer", "supervisor.chennai@demo.floorpulse.app", "E004", [Role.supervisor], ["CHE"]),
    ("Vikram Singh", "tech@demo.floorpulse.app", "E005", [Role.technician], ["PUN", "CHE"]),
    ("Arjun Nair", "tech2@demo.floorpulse.app", "E006", [Role.technician, Role.operator], ["CHE"]),
    ("Priya Sharma", "quality@demo.floorpulse.app", "E007", [Role.inspector], ["PUN", "CHE"]),
    ("Farhan Shaikh", "stores@demo.floorpulse.app", "E008", [Role.storekeeper], ["PUN", "CHE"]),
    ("Ganesh Jadhav", None, "E101", [Role.operator], ["PUN"]),
    ("Lakshmi Rao", None, "E102", [Role.operator], ["PUN"]),
    ("Mohan Das", None, "E103", [Role.operator], ["CHE"]),
    ("Kavita Joshi", None, "E104", [Role.operator], ["CHE"]),
]


@dataclass
class DemoRefs:
    org: Organization
    sites: dict[str, Site] = field(default_factory=dict)
    areas: dict[str, Area] = field(default_factory=dict)  # key "PUN/MCH"
    users: dict[str, User] = field(default_factory=dict)  # key employee code
    device_tokens: dict[str, str] = field(default_factory=dict)  # site code -> raw token


def demo_device_token(site_code: str) -> str:
    """Known device tokens so the demo can PIN-login without registering. Demo data only."""
    return f"demo-device-{site_code.lower()}"


def seed_core(db: Session, rng: random.Random) -> DemoRefs:
    org = Organization(name=DEMO_ORG, slug="demo", settings={"currency": "INR", "timezone": "Asia/Kolkata"})
    db.add(org)
    db.flush()
    refs = DemoRefs(org)
    for name, code, tz, lines in SITES:
        site = Site(organization_id=org.id, name=name, code=code, timezone=tz)
        db.add(site)
        db.flush()
        refs.sites[code] = site
        for lname, lcode in lines:
            area = Area(organization_id=org.id, site_id=site.id, name=lname, code=lcode)
            db.add(area)
            refs.areas[f"{code}/{lcode}"] = area
    db.flush()

    pw_hash = hash_secret(DEMO_PASSWORD)
    pin_hash = hash_secret(DEMO_PIN)
    for name, email, ecode, roles, site_codes in USERS:
        shop_floor = bool(
            {Role.operator, Role.supervisor, Role.technician, Role.inspector, Role.storekeeper} & set(roles)
        )
        u = User(
            organization_id=org.id,
            name=name,
            email=email,
            employee_code=ecode,
            password_hash=pw_hash if email else None,
            pin_hash=pin_hash if shop_floor else None,
            pin_length=len(DEMO_PIN) if shop_floor else None,
            roles=[UserRole(role=r.value) for r in roles],
            sites=[UserSite(site_id=refs.sites[c].id) for c in site_codes],
        )
        db.add(u)
        refs.users[ecode] = u
    db.flush()

    for code, site in refs.sites.items():
        raw = demo_device_token(code)
        db.add(
            Device(
                organization_id=org.id,
                name=f"{site.name} shop-floor tablet",
                token_hash=sha256(raw),
                site_id=site.id,
            )
        )
        refs.device_tokens[code] = raw
    audit.record(db, None, "seed.demo", "organization", org.id, org_id=org.id, note="demo data generated")
    db.flush()
    return refs


def seed(db: Session, seed_value: int = 42) -> DemoRefs:
    rng = random.Random(seed_value)
    refs = seed_core(db, rng)
    db.commit()
    return refs
