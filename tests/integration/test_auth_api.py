import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield


import uuid


def test_user_registration_success():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "Senior FullStack Candidate",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["full_name"] == "Senior FullStack Candidate"
        assert "id" in data



def test_user_registration_duplicate_email():
    with TestClient(app) as client:
        # First register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup_candidate@example.com",
                "password": "Password123!",
            },
        )
        # Duplicate register
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup_candidate@example.com",
                "password": "AnotherPassword123!",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["error"]["message"]


def test_user_login_success():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_candidate@example.com",
                "password": "Password123!",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login_candidate@example.com",
                "password": "Password123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


def test_user_login_invalid_password():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "bad_pw_candidate@example.com",
                "password": "Password123!",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "bad_pw_candidate@example.com",
                "password": "WrongPassword!",
            },
        )
        assert response.status_code == 401


def test_get_current_user_authenticated_and_unauthenticated():
    with TestClient(app) as client:
        unauth_response = client.get("/api/v1/auth/me")
        assert unauth_response.status_code == 401

        client.post(
            "/api/v1/auth/register",
            json={
                "email": "me_candidate@example.com",
                "password": "Password123!",
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "me_candidate@example.com",
                "password": "Password123!",
            },
        )
        token = login_response.json()["access_token"]

        auth_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert auth_response.status_code == 200
        user_data = auth_response.json()
        assert user_data["email"] == "me_candidate@example.com"
