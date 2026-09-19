import uuid
from typing import BinaryIO, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.db.models.document import Document
from app.db.models.page import DocumentPage
from app.db.models.user import User
from app.services.storage_service import StorageService


class DocumentService:
    @staticmethod
    def create_document(
        db: Session,
        user: User,
        file_obj: BinaryIO,
        filename: str,
        storage_service: StorageService,
    ) -> Document:
        """Saves an uploaded file to storage and creates an initial Document record in the DB."""
        stored_filename, mime_type, file_size = storage_service.save_file(
            file_obj=file_obj, original_filename=filename
        )

        document = Document(
            user_id=user.id,
            filename=filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_size_bytes=file_size,
            processing_status="UPLOADED",
            processing_stage="INIT",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def get_document_by_id(db: Session, document_id: uuid.UUID, user: User) -> Document:
        """Retrieves a document by ID, enforcing that the requesting user is the owner."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise EntityNotFoundException("Document", document_id)

        if document.user_id != user.id:
            # We raise 404 or 403 to avoid leaking existence
            raise ForbiddenException("You do not have permission to access this document.")

        return document

    @staticmethod
    def list_user_documents(
        db: Session,
        user: User,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Document], int]:
        """Lists documents owned by a user with optional status filtering and pagination."""
        query = db.query(Document).filter(Document.user_id == user.id)
        if status_filter:
            query = query.filter(Document.processing_status == status_filter.upper())

        total = query.count()
        items = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def get_document_pages(
        db: Session, document_id: uuid.UUID, user: User
    ) -> List[DocumentPage]:
        """Retrieves the normalized pages of a document after ownership verification."""
        document = DocumentService.get_document_by_id(db, document_id, user)
        return document.pages

    @staticmethod
    def delete_document(
        db: Session,
        document_id: uuid.UUID,
        user: User,
        storage_service: StorageService,
    ) -> bool:
        """Deletes a document, its physical files, and all associated extracted data."""
        document = DocumentService.get_document_by_id(db, document_id, user)
        # Delete underlying physical file
        storage_service.delete_file(document.stored_filename)

        # Delete database record (cascades to pages, questions, options, reviews, etc.)
        db.delete(document)
        db.commit()
        return True
