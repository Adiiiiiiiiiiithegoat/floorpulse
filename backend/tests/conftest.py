import os

os.environ["FP_ENV"] = "test"
os.environ["FP_DATABASE_URL"] = "sqlite://"
os.environ["FP_LOG_JSON"] = "false"
os.environ["FP_LOG_LEVEL"] = "WARNING"

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine
from app.core.security import limiter
from app.main import app
from app.models import Base
from tests.factories import Tenant, make_tenant


@pytest.fixture(autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.create_all(engine)
    limiter.reset()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tenant(db: Session) -> Tenant:
    return make_tenant(db, "acme")


@pytest.fixture
def other_tenant(db: Session) -> Tenant:
    return make_tenant(db, "rival")
