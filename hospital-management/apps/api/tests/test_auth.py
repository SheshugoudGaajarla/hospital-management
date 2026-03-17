from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.core.config import settings
from app.core.metrics import metrics_store
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import user as _user_models
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module() -> None:
    _ = _user_models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    rate_limiter.reset()
    metrics_store.reset()

client = TestClient(app)


def test_bootstrap_admin_and_login_flow() -> None:
    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "username": "admin",
            "full_name": "System Admin",
            "password": "admin1234",
        },
    )
    assert bootstrap_response.status_code == 201

    second_bootstrap = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "username": "admin2",
            "full_name": "Another Admin",
            "password": "admin1234",
        },
    )
    assert second_bootstrap.status_code == 409

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin1234"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "admin"

    admin_response = client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_response.status_code == 200

    create_user_response = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "doctor_ped",
            "full_name": "Dr Viday Sagar Reddy",
            "role": "doctor",
            "password": "doctor1234",
        },
    )
    assert create_user_response.status_code == 201
    assert create_user_response.json()["role"] == "doctor"

    users_response = client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert users_response.status_code == 200
    assert any(user["username"] == "doctor_ped" for user in users_response.json())


def test_login_rate_limit_enforced() -> None:
    rate_limiter.reset()
    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "username": "ratelimit-admin",
            "full_name": "Rate Limit Admin",
            "password": "admin1234",
        },
    )
    if bootstrap_response.status_code not in {201, 409}:
        assert False, bootstrap_response.text

    for _ in range(settings.rate_limit_login_per_minute):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "ratelimit-admin", "password": "wrong-password"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/v1/auth/login",
        json={"username": "ratelimit-admin", "password": "wrong-password"},
    )
    assert blocked.status_code == 429
    rate_limiter.reset()
