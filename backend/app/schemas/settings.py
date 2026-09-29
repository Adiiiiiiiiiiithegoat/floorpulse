from typing import Literal

from pydantic import BaseModel, Field


class AlertThresholds(BaseModel):
    long_stop_supervisor_min: int = 15
    long_stop_manager_min: int = 60
    oee_below_pct: float = 50.0
    reject_rate_above_pct: float = 5.0
    unexplained_gap_min: int = 20


class OrgSettings(BaseModel):
    """Per-organization configuration. Stored as JSON on organizations.settings; defaults fill gaps."""

    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    default_language: str = "en"
    week_start_day: int = Field(0, ge=0, le=6)  # 0 = Monday
    unit_system: Literal["metric", "imperial"] = "metric"
    working_days: list[int] = [0, 1, 2, 3, 4, 5]  # Mon-Sat
    oee_ideal_rate_mode: Literal["machine", "product"] = "product"
    planned_changeovers: bool = False  # count changeovers as planned stops in OEE
    allow_negative_stock: bool = False
    backflush_on_output: bool = False
    low_stock_default_days: int = 7
    show_operator_analytics: bool = False  # privacy: off by default
    data_retention_days: int = 3 * 365
    alert_thresholds: AlertThresholds = AlertThresholds()
    alert_channels: list[Literal["in_app", "email", "push", "whatsapp", "sms"]] = ["in_app"]
    digest_time: str = "07:00"
    weekly_summary_day: int = Field(0, ge=0, le=6)
    require_2fa_for_admins: bool = False
    operator_idle_lock_min: int = Field(10, ge=1, le=480)  # operator app auto-locks after inactivity


def load_settings(raw: dict[str, object] | None) -> OrgSettings:
    return OrgSettings.model_validate(raw or {})
