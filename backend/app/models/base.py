from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, MetaData, func
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.time import utcnow


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC, returns aware UTC. Works the same on SQLite and Postgres."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime column")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime(), dict[str, Any]: JSON(), list[Any]: JSON()}


class IdMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow, onupdate=utcnow, server_default=func.current_timestamp()
    )


class OrgMixin:
    @declared_attr
    def organization_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)


class CreatedByMixin:
    @declared_attr
    def created_by(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ArchiveMixin:
    archived_at: Mapped[datetime | None] = mapped_column(default=None)


class TenantModel(IdMixin, TimestampMixin, OrgMixin, CreatedByMixin, Base):
    """Standard business row: id, org scope, timestamps, creator."""

    __abstract__ = True
