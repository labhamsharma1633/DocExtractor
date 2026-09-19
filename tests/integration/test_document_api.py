import io
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def auth_headers_user1():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "docuser1_unique@example.com", "password": "Password123!"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "docuser1_unique@example.com", "password": "Password123!"},
        )
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "docuser2_unique@example.com", "password": "Password123!"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "docuser2_unique@example.com", "password": "Password123!"},
        )
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


def test_upload_valid_pdf(auth_headers_user1):
    with TestClient(app) as client:
        with open("samples/clean_digital.pdf", "rb") as f:
            response = client.post(
                "/api/v1/documents",
                headers=auth_headers_user1,
                files={"file": ("sample_exam.pdf", f, "application/pdf")},
            )
        assert response.status_code == 202
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "sample_exam.pdf"


def test_upload_valid_png_image(auth_headers_user1):
    with TestClient(app) as client:
        with open("samples/sample_question.png", "rb") as f:
            response = client.post(
                "/api/v1/documents",
                headers=auth_headers_user1,
                files={"file": ("question_image.png", f, "image/png")},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["filename"] == "question_image.png"


def test_upload_unsupported_file_format(auth_headers_user1):
    with TestClient(app) as client:
        txt_bytes = b"Hello world, this is a plain text file that is not allowed."
        file_obj = io.BytesIO(txt_bytes)
        
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers_user1,
            files={"file": ("invalid_file.txt", file_obj, "text/plain")},
        )
        assert response.status_code == 415
        data = response.json()
        assert "Unsupported media type" in data["error"]["message"]


def test_list_and_get_user_documents(auth_headers_user1):
    with TestClient(app) as client:
        with open("samples/clean_digital.pdf", "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents",
                headers=auth_headers_user1,
                files={"file": ("list_test.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        # List documents
        list_resp = client.get("/api/v1/documents", headers=auth_headers_user1)
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert any(d["id"] == doc_id for d in list_data["items"])

        # Get document detail
        detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user1)
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == doc_id
        assert detail_data["filename"] == "list_test.pdf"


def test_user_ownership_isolation(auth_headers_user1, auth_headers_user2):
    with TestClient(app) as client:
        with open("samples/clean_digital.pdf", "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents",
                headers=auth_headers_user1,
                files={"file": ("private_exam.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        # User 2 tries to access User 1's document -> Forbidden (403)
        access_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user2)
        assert access_resp.status_code == 403

        # User 2 tries to delete User 1's document -> Forbidden (403)
        delete_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_user2)
        assert delete_resp.status_code == 403


def test_delete_document_success(auth_headers_user1):
    with TestClient(app) as client:
        with open("samples/clean_digital.pdf", "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents",
                headers=auth_headers_user1,
                files={"file": ("to_delete.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        # Delete document
        delete_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_user1)
        assert delete_resp.status_code == 204

        # Verify not found
        get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user1)
        assert get_resp.status_code == 404
