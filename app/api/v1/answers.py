import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.db.models.answer_key import AnswerKey
from app.db.models.document import Document
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.answer import AnswerKeyListResponse, AnswerKeyResponse

router = APIRouter(prefix="/documents", tags=["Answers"])


@router.get(
    "/{document_id}/answers",
    response_model=AnswerKeyListResponse,
    summary="Get all raw and parsed answer keys for a document",
)
def get_document_answers(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves answer key blocks parsed from the document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise EntityNotFoundException("Document", document_id)

    if document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to view answers for this document.")

    answer_keys = db.query(AnswerKey).filter(AnswerKey.document_id == document_id).all()
    return AnswerKeyListResponse(total=len(answer_keys), items=answer_keys)
