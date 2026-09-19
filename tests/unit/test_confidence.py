import uuid
import pytest
from app.schemas.page import PageContent
from app.services.confidence_service import ConfidenceService
from app.services.parser_service import ParsedOption, ParsedQuestion


def test_high_confidence_mcq_extraction():
    doc_id = uuid.uuid4()
    pages_map = {
        1: PageContent(
            document_id=doc_id,
            page_number=1,
            extracted_text="Some text",
            ocr_used=False,
        )
    }

    q = ParsedQuestion(
        question_number="1",
        question_text="Which layer in the OSI model is responsible for routing packets?",
        options=[
            ParsedOption("A", "Physical"),
            ParsedOption("B", "Data Link"),
            ParsedOption("C", "Network"),
            ParsedOption("D", "Transport"),
        ],
        source_pages=[1],
        question_type="MCQ",
    )
    q.matched_answer = "C"

    score, status, reviews = ConfidenceService.evaluate_question(doc_id, q, pages_map)
    assert score == 1.0
    assert status == "EXTRACTED"
    assert len(reviews) == 0


def test_low_confidence_missing_options():
    doc_id = uuid.uuid4()
    pages_map = {
        1: PageContent(
            document_id=doc_id,
            page_number=1,
            extracted_text="Some text",
            ocr_used=True,
            ocr_confidence=45.0,  # Low OCR confidence
        )
    }

    q = ParsedQuestion(
        question_number=None,  # Missing question number
        question_text="Incomplete fragment",
        options=[],  # Missing options for MCQ
        source_pages=[1],
        question_type="MCQ",
    )

    score, status, reviews = ConfidenceService.evaluate_question(doc_id, q, pages_map)
    assert score < 0.60
    assert status == "REVIEW"
    review_types = [r["review_type"] for r in reviews]
    assert "MISSING_QUESTION_NUMBER" in review_types
    assert "MISSING_OPTIONS" in review_types
    assert "OCR_UNCERTAINTY" in review_types
