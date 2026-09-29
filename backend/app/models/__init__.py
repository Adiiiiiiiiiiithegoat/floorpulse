"""Import every model module so Base.metadata is complete (Alembic, tests)."""

from app.models.audit import AuditLog, JobRun
from app.models.base import Base
from app.models.org import Area, Device, Organization, RefreshToken, Role, Site, User, UserRole, UserSite

__all__ = [
    "Area",
    "AuditLog",
    "Base",
    "Device",
    "JobRun",
    "Organization",
    "RefreshToken",
    "Role",
    "Site",
    "User",
    "UserRole",
    "UserSite",
]
