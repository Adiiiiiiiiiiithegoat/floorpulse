from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORM


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=200)
    totp_code: str | None = Field(None, max_length=10)


class PinLoginIn(BaseModel):
    user_id: int
    pin: str = Field(pattern=r"^\d{4,6}$")


class MeOut(ORM):
    id: int
    organization_id: int
    name: str
    email: str | None
    employee_code: str | None
    roles: list[str]
    site_ids: list[int]
    language: str | None
    totp_enabled: bool
    organization_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    user: MeOut


class SessionOut(BaseModel):
    id: str  # family id
    auth_method: str
    user_agent: str | None
    ip: str | None
    created_at: datetime
    last_used_at: datetime | None
    current: bool


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TotpCodeIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class DeviceRegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    site_id: int
    area_id: int | None = None


class DeviceRegisterOut(BaseModel):
    id: int
    device_token: str
    site_id: int
    area_id: int | None


class DeviceOperatorOut(ORM):
    id: int
    name: str
    employee_code: str | None
    pin_length: int | None


class DeviceInfoOut(BaseModel):
    id: int
    name: str
    site_id: int
    site_name: str
    area_id: int | None
    organization_name: str
    operators: list[DeviceOperatorOut]


class PinChangeIn(BaseModel):
    pin: str = Field(pattern=r"^\d{4,6}$")


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)
