import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database schema is created before tests run."""
    Base.metadata.create_all(bind=engine)
    yield


def test_health_check():
    """Verify that the FastAPI application is alive and healthy."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


def test_root_endpoint():
    """Verify the root UI/API endpoint."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        # If static dashboard is mounted, returns HTML content; otherwise JSON metadata
        if "text/html" in response.headers.get("content-type", ""):
            assert "<!DOCTYPE html>" in response.text or "DocExtractor" in response.text
        else:
            data = response.json()
            assert "docs" in data
