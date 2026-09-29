from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_secret
from app.models.org import Area, Organization, Role, Site, User, UserRole, UserSite

PASSWORD = "correct-horse-battery"
PIN = "1234"


@dataclass
class Tenant:
    org: Organization
    site: Site
    area: Area
    users: dict[Role, User] = field(default_factory=dict)

    def headers(self, role: Role = Role.admin) -> dict[str, str]:
        return auth_headers(self.users[role])


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.organization_id, sorted(user.role_set))
    return {"Authorization": f"Bearer {token}"}


def make_user(
    db: Session, org: Organization, site: Site, role: Role, email: str | None = None, pin: str | None = PIN
) -> User:
    u = User(
        organization_id=org.id,
        name=f"{org.slug} {role.value}",
        email=email,
        employee_code=f"{org.slug}-{role.value}",
        password_hash=hash_secret(PASSWORD),
        pin_hash=hash_secret(pin) if pin else None,
        pin_length=len(pin) if pin else None,
        roles=[UserRole(role=role.value)],
        sites=[UserSite(site_id=site.id)],
    )
    db.add(u)
    db.flush()
    return u


def make_tenant(db: Session, slug: str) -> Tenant:
    org = Organization(name=f"{slug.title()} Ltd", slug=slug, settings={})
    db.add(org)
    db.flush()
    site = Site(organization_id=org.id, name=f"{slug} plant", code="P1", timezone="Asia/Kolkata")
    db.add(site)
    db.flush()
    area = Area(organization_id=org.id, site_id=site.id, name="Line 1", code="L1")
    db.add(area)
    db.flush()
    t = Tenant(org, site, area)
    for role in Role:
        t.users[role] = make_user(db, org, site, role, email=f"{role.value}@{slug}.test")
    db.commit()
    return t
