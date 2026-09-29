from datetime import datetime
from typing import Any
from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.org import Role
from app.schemas.common import ORM


def _check_tz(v: str | None) -> str | None:
    if v is not None and v not in available_timezones():
        raise ValueError("unknown time zone")
    return v


class SiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=40)
    timezone: str = "Asia/Kolkata"
    address: str | None = Field(None, max_length=500)

    _tz = field_validator("timezone")(_check_tz)


class SitePatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=40)
    timezone: str | None = None
    address: str | None = Field(None, max_length=500)
    archived: bool | None = None

    _tz = field_validator("timezone")(_check_tz)


class SiteOut(ORM):
    id: int
    name: str
    code: str
    timezone: str
    address: str | None
    archived_at: datetime | None
    updated_at: datetime


class AreaIn(BaseModel):
    site_id: int
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=40)


class AreaPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=40)
    archived: bool | None = None


class AreaOut(ORM):
    id: int
    site_id: int
    name: str
    code: str
    archived_at: datetime | None
    updated_at: datetime


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    employee_code: str | None = Field(None, max_length=40)
    phone: str | None = Field(None, max_length=40)
    password: str | None = Field(None, min_length=10, max_length=200)
    pin: str | None = Field(None, pattern=r"^\d{4,6}$")
    roles: list[Role] = Field(min_length=1)
    site_ids: list[int] = []
    language: str | None = Field(None, max_length=10)


class UserPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    employee_code: str | None = Field(None, max_length=40)
    phone: str | None = Field(None, max_length=40)
    password: str | None = Field(None, min_length=10, max_length=200)
    pin: str | None = Field(None, pattern=r"^\d{4,6}$")
    roles: list[Role] | None = Field(None, min_length=1)
    site_ids: list[int] | None = None
    language: str | None = Field(None, max_length=10)
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str | None
    employee_code: str | None
    phone: str | None
    roles: list[str]
    site_ids: list[int]
    language: str | None
    is_active: bool
    has_pin: bool
    has_password: bool
    totp_enabled: bool
    last_login_at: datetime | None
    updated_at: datetime


class AuditOut(ORM):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    note: str | None
    ip: str | None
    request_id: str | None
    created_at: datetime
