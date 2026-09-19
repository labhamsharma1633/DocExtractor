import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.db.models.document import Document
from app.db.models.question import Question
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.question import (
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter(tags=["Questions"])


@router.get(
    "/documents/{document_id}/questions",
    response_model=QuestionListResponse,
    summary="Get all extracted structured questions for a document",
)
def get_document_questions(
    document_id: uuid.UUID,
    question_type: Optional[str] = Query(None, alias="type", description="Filter by question type"),
    extraction_status: Optional[str] = Query(None, alias="status", description="Filter by status (EXTRACTED, PARTIAL, REVIEW)"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all extracted questions from a document with optional filtering."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise EntityNotFoundException("Document", document_id)
    if document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to access this document's questions.")

    query = db.query(Question).filter(Question.document_id == document_id)
    if question_type:
        query = query.filter(Question.question_type == question_type.upper())
    if extraction_status:
        query = query.filter(Question.extraction_status == extraction_status.upper())
    if min_confidence is not None:
        query = query.filter(Question.confidence_score >= min_confidence)

    items = query.all()

    # Format responses with source_pages
    response_items = []
    for q in items:
        src_pages = [s.page_number for s in q.sources]
        resp_q = QuestionResponse(
            id=q.id,
            document_id=q.document_id,
            question_number=q.question_number,
            question_text=q.question_text,
            question_type=q.question_type,
            confidence_score=q.confidence_score,
            extraction_status=q.extraction_status,
            matched_answer=q.matched_answer,
            answer_source=q.answer_source,
            options=q.options,
            source_pages=src_pages,
            created_at=q.created_at,
            updated_at=q.updated_at,
        )
        response_items.append(resp_q)

    return QuestionListResponse(total=len(response_items), items=response_items)


@router.get(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Get details of a single extracted question",
)
def get_question_by_id(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves single question details including its options and source pages."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise EntityNotFoundException("Question", question_id)

    if question.document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to access this question.")

    src_pages = [s.page_number for s in question.sources]
    return QuestionResponse(
        id=question.id,
        document_id=question.document_id,
        question_number=question.question_number,
        question_text=question.question_text,
        question_type=question.question_type,
        confidence_score=question.confidence_score,
        extraction_status=question.extraction_status,
        matched_answer=question.matched_answer,
        answer_source=question.answer_source,
        options=question.options,
        source_pages=src_pages,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.patch(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Update or correct an extracted question",
)
def update_question(
    question_id: uuid.UUID,
    update_in: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows human reviewers to update/correct question text, type, or matched answer."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise EntityNotFoundException("Question", question_id)

    if question.document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to edit this question.")

    if update_in.question_text is not None:
        question.question_text = update_in.question_text
    if update_in.question_type is not None:
        question.question_type = update_in.question_type.upper()
    if update_in.matched_answer is not None:
        question.matched_answer = update_in.matched_answer.upper()
        question.answer_source = "MANUAL"

    db.commit()
    db.refresh(question)

    src_pages = [s.page_number for s in question.sources]
    return QuestionResponse(
        id=question.id,
        document_id=question.document_id,
        question_number=question.question_number,
        question_text=question.question_text,
        question_type=question.question_type,
        confidence_score=question.confidence_score,
        extraction_status=question.extraction_status,
        matched_answer=question.matched_answer,
        answer_source=question.answer_source,
        options=question.options,
        source_pages=src_pages,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )
