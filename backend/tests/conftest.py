from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user, get_or_create_user
from app.db import get_db, make_engine
from app.main import app
from app.models import Base
from app.storage import LocalStorage, get_storage

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def db():
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        yield session
    engine.dispose()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "uploads")


@pytest.fixture
def clients(db, storage):
    from fastapi import Request

    def resolve(request: Request):
        return get_or_create_user(db, request.headers["X-Test-User"])

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_current_user] = resolve

    def as_user(subject: str) -> TestClient:
        client = TestClient(app)
        client.headers["X-Test-User"] = subject
        return client

    yield as_user
    app.dependency_overrides.clear()


@pytest.fixture
def client(clients):
    return clients("alice")


def upload(client: TestClient, filename: str, account_name: str = "Checking", account_type="checking"):
    accounts = {a["name"]: a for a in client.get("/api/accounts").json()}
    account = accounts.get(account_name) or client.post(
        "/api/accounts", json={"name": account_name, "account_type": account_type}
    ).json()
    resp = client.post(
        "/api/uploads",
        data={"account_id": str(account["id"])},
        files={"file": (filename, fixture_bytes(filename), "text/csv")},
    )
    return resp, account
