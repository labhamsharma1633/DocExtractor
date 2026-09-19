import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import AppException, EntityNotFoundException, ForbiddenException
from app.db.models.document import Document
from app.db.models.relationship import DocumentRelationship
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.relationship import (
    RelationshipCreate,
    RelationshipListResponse,
    RelationshipResponse,
)

router = APIRouter(prefix="/documents", tags=["Relationships"])


@router.post(
    "/{document_id}/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a relationship between two documents (e.g., Question Paper + Answer Key)",
)
def create_document_relationship(
    document_id: uuid.UUID,
    rel_in: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Links a document to another document, such as associating an external answer key document."""
    source_doc = db.query(Document).filter(Document.id == document_id).first()
    if not source_doc:
        raise EntityNotFoundException("Document", document_id)
    if source_doc.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to modify this document.")

    related_doc = db.query(Document).filter(Document.id == rel_in.related_document_id).first()
    if not related_doc:
        raise EntityNotFoundException("Related Document", rel_in.related_document_id)
    if related_doc.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to link to this related document.")

    if source_doc.id == related_doc.id:
        raise AppException("A document cannot be linked to itself.")

    # Check for existing relationship
    existing = (
        db.query(DocumentRelationship)
        .filter(
            DocumentRelationship.source_document_id == source_doc.id,
            DocumentRelationship.related_document_id == related_doc.id,
        )
        .first()
    )
    if existing:
        return existing

    new_rel = DocumentRelationship(
        source_document_id=source_doc.id,
        related_document_id=related_doc.id,
        relationship_type=rel_in.relationship_type.upper(),
    )
    db.add(new_rel)
    db.commit()
    db.refresh(new_rel)
    return new_rel


@router.get(
    "/{document_id}/relationships",
    response_model=RelationshipListResponse,
    summary="Get all related documents for a document",
)
def get_document_relationships(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all documents related to the specified document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise EntityNotFoundException("Document", document_id)
    if document.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to view relationships for this document.")

    relationships = (
        db.query(DocumentRelationship)
        .filter(DocumentRelationship.source_document_id == document_id)
        .all()
    )
    return RelationshipListResponse(total=len(relationships), items=relationships)
