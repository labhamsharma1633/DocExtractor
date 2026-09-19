import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.db.models.document import Document
from app.db.models.review_item import ReviewItem
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.review import ReviewItemListResponse, ReviewItemResponse

router = APIRouter(tags=["Reviews"])


@router.get(
    "/documents/{document_id}/review-items",
    response_model=ReviewItemListResponse,
    summary="Get all review items / flagged quality issues for a document",
)
def get_document_review_items(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all quality issues flagged for human review on a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise EntityNotFoundException("Document", document_id)

    if document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to view review items for this document.")

    items = db.query(ReviewItem).filter(ReviewItem.document_id == document_id).all()
    return ReviewItemListResponse(total=len(items), items=items)


@router.patch(
    "/review-items/{review_item_id}/resolve",
    response_model=ReviewItemResponse,
    summary="Mark a quality review item as resolved",
)
def resolve_review_item(
    review_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marks a specific review warning item as resolved by a human operator."""
    review_item = db.query(ReviewItem).filter(ReviewItem.id == review_item_id).first()
    if not review_item:
        raise EntityNotFoundException("ReviewItem", review_item_id)

    if review_item.document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to update this review item.")

    review_item.is_resolved = True
    db.commit()
    db.refresh(review_item)
    return review_item
