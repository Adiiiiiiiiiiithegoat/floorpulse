import enum
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import hash_secret
from app.models.base import ArchiveMixin, Base, IdMixin, TenantModel, TimestampMixin


class Role(enum.StrEnum):
    operator = "operator"
    supervisor = "supervisor"
    technician = "technician"
    inspector = "inspector"
    storekeeper = "storekeeper"
    manager = "manager"
    admin = "admin"


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    # Validated through app.schemas.settings.OrgSettings; stored as JSON so new settings need no migration.
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)
    logo_path: Mapped[str | None] = mapped_column(String(300), default=None)


class Site(TenantModel, ArchiveMixin):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    address: Mapped[str | None] = mapped_column(String(500), default=None)

    areas: Mapped[list["Area"]] = relationship(back_populates="site", lazy="raise")


class Area(TenantModel, ArchiveMixin):
    """A production area or line inside a site."""

    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("site_id", "code"),)

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40))

    site: Mapped[Site] = relationship(back_populates="areas", lazy="raise")


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "employee_code"),
        Index("ix_users_email_lower", "email", unique=True),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(
        String(254), default=None
    )  # lower-cased; operators may have none
    employee_code: Mapped[str | None] = mapped_column(String(40), default=None)  # badge QR value
    phone: Mapped[str | None] = mapped_column(String(40), default=None)
    password_hash: Mapped[str | None] = mapped_column(String(300), default=None)
    pin_hash: Mapped[str | None] = mapped_column(String(300), default=None)
    pin_length: Mapped[int | None] = mapped_column(default=None)  # lets the PIN pad auto-submit
    failed_pin_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(default=None)
    totp_secret: Mapped[str | None] = mapped_column(String(64), default=None)
    totp_enabled: Mapped[bool] = mapped_column(default=False)
    language: Mapped[str | None] = mapped_column(String(10), default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
    deactivated_at: Mapped[datetime | None] = mapped_column(default=None)

    roles: Mapped[list["UserRole"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", back_populates="user"
    )
    sites: Mapped[list["UserSite"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", back_populates="user"
    )

    def set_pin(self, pin: str) -> None:
        self.pin_hash = hash_secret(pin)
        self.pin_length = len(pin)
        self.failed_pin_attempts = 0
        self.locked_until = None

    @property
    def role_set(self) -> set[Role]:
        return {Role(r.role) for r in self.roles}

    @property
    def site_ids(self) -> list[int]:
        return [s.site_id for s in self.sites]


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), primary_key=True)

    user: Mapped[User] = relationship(back_populates="roles")


class UserSite(Base):
    __tablename__ = "user_sites"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped[User] = relationship(back_populates="sites")


class Device(TenantModel):
    """A registered shop-floor device (shared phone/tablet) that operators PIN into."""

    __tablename__ = "devices"

    name: Mapped[str] = mapped_column(String(120))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)


class RefreshToken(IdMixin, Base):
    """One row per issued refresh token. A 'family' is one login session; rotation keeps the family."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[str] = mapped_column(String(32), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), default=None)
    auth_method: Mapped[str] = mapped_column(String(10), default="password")
    user_agent: Mapped[str | None] = mapped_column(String(300), default=None)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
