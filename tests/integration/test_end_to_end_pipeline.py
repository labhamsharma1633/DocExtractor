import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.pipeline_service import DocumentPipelineService


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def auth_headers():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "e2e_tester@example.com", "password": "Password123!"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "e2e_tester@example.com", "password": "Password123!"},
        )
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


def test_clean_digital_pdf_e2e(auth_headers):
    with TestClient(app) as client:
        # 1. Upload Clean Digital PDF
        with open("samples/clean_digital.pdf", "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("clean_digital.pdf", f, "application/pdf")},
            )
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]

        # 2. Run Pipeline (Synchronously for reliable testing)
        db = SessionLocal()
        try:
            pipeline = DocumentPipelineService()
            pipeline.run_pipeline(uuid.UUID(doc_id), db)
        finally:
            db.close()

        # 3. Verify Document Status
        doc_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert doc_data["processing_status"] in ["COMPLETED", "PARTIAL"]
        assert doc_data["questions_count"] == 4
        assert doc_data["pages_count"] == 1
        assert doc_data["overall_confidence"] >= 0.85

        # 4. Verify Extracted Questions
        q_resp = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
        assert q_resp.status_code == 200
        q_data = q_resp.json()
        assert q_data["total"] == 4
        questions = q_data["items"]

        # Question 1 (TCP transport layer)
        q1 = questions[0]
        assert q1["question_number"] == "1"
        assert "transport layer protocols" in q1["question_text"]
        assert q1["question_type"] == "MCQ"
        assert len(q1["options"]) == 4
        assert q1["matched_answer"] == "B"
        assert q1["source_pages"] == [1]

        # Question 4 (Descriptive)
        q4 = questions[3]
        assert q4["question_number"] == "4"
        assert "Explain the difference" in q4["question_text"]
        assert q4["question_type"] == "DESCRIPTIVE"
        assert len(q4["options"]) == 0

        # 5. Verify Answer Keys Endpoint
        ans_resp = client.get(f"/api/v1/documents/{doc_id}/answers", headers=auth_headers)
        assert ans_resp.status_code == 200
        assert ans_resp.json()["total"] >= 1


def test_multipage_question_pdf_e2e(auth_headers):
    with TestClient(app) as client:
        # 1. Upload Multi-page PDF
        with open("samples/multipage_question.pdf", "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("multipage_question.pdf", f, "application/pdf")},
            )
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]

        # 2. Run Pipeline
        db = SessionLocal()
        try:
            pipeline = DocumentPipelineService()
            pipeline.run_pipeline(uuid.UUID(doc_id), db)
        finally:
            db.close()

        # 3. Verify Questions & Cross-Page Stitching
        q_resp = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
        assert q_resp.status_code == 200
        questions = q_resp.json()["items"]
        assert len(questions) == 3

        # Question 2 spanned across page 1 and page 2
        q2 = next(q for q in questions if q["question_number"] == "2")
        assert q2["source_pages"] == [1, 2]
        assert len(q2["options"]) == 4
        assert q2["options"][0]["option_key"] == "A"
        assert q2["options"][2]["option_key"] == "C"
        assert q2["options"][3]["option_key"] == "D"
        assert q2["matched_answer"] == "A"


def test_document_relationships_and_review_resolution(auth_headers):
    with TestClient(app) as client:
        # 1. Upload Question Doc
        with open("samples/clean_digital.pdf", "rb") as f:
            up1 = client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("exam.pdf", f, "application/pdf")},
            )
        doc1_id = up1.json()["document_id"]

        # 2. Upload Separate Answer Key Doc
        with open("samples/separate_answer_key.pdf", "rb") as f:
            up2 = client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("key.pdf", f, "application/pdf")},
            )
        doc2_id = up2.json()["document_id"]

        # 3. Create Relationship
        rel_resp = client.post(
            f"/api/v1/documents/{doc1_id}/relationships",
            headers=auth_headers,
            json={"related_document_id": doc2_id, "relationship_type": "ANSWER_KEY"},
        )
        assert rel_resp.status_code == 201
        rel_data = rel_resp.json()
        assert rel_data["relationship_type"] == "ANSWER_KEY"

        # 4. Get Relationships
        list_rel = client.get(f"/api/v1/documents/{doc1_id}/relationships", headers=auth_headers)
        assert list_rel.status_code == 200
        assert list_rel.json()["total"] == 1

        # 5. Process Doc 1 and Test Review Items
        db = SessionLocal()
        try:
            pipeline = DocumentPipelineService()
            pipeline.run_pipeline(uuid.UUID(doc1_id), db)
        finally:
            db.close()

        rev_resp = client.get(f"/api/v1/documents/{doc1_id}/review-items", headers=auth_headers)
        assert rev_resp.status_code == 200
        review_items = rev_resp.json()["items"]
        if review_items:
            rev_id = review_items[0]["id"]
            # Resolve review item
            patch_resp = client.patch(f"/api/v1/review-items/{rev_id}/resolve", headers=auth_headers)
            assert patch_resp.status_code == 200
            assert patch_resp.json()["is_resolved"] is True


def test_manual_question_correction(auth_headers):
    with TestClient(app) as client:
        with open("samples/clean_digital.pdf", "rb") as f:
            up = client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("edit_test.pdf", f, "application/pdf")},
            )
        doc_id = up.json()["document_id"]

        db = SessionLocal()
        try:
            pipeline = DocumentPipelineService()
            pipeline.run_pipeline(uuid.UUID(doc_id), db)
        finally:
            db.close()

        q_resp = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
        question = q_resp.json()["items"][0]
        q_id = question["id"]

        # Human operator corrects question
        patch_resp = client.patch(
            f"/api/v1/questions/{q_id}",
            headers=auth_headers,
            json={
                "question_text": "Updated Question: What is TCP?",
                "matched_answer": "B",
            },
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["question_text"] == "Updated Question: What is TCP?"
        assert data["matched_answer"] == "B"
        assert data["answer_source"] == "MANUAL"
