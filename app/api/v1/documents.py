import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.page import PageResponse
from app.services.document_service import DocumentService
from app.services.pipeline_service import DocumentPipelineService
from app.services.storage_service import StorageService, get_storage_service
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["Documents"])


def _dispatch_processing(document_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session):
    """Dispatches processing instantly to background task, avoiding Redis socket hang."""
    def run_sync_pipeline(doc_uuid: uuid.UUID):
        from app.db.session import SessionLocal
        local_db = SessionLocal()
        try:
            pipeline = DocumentPipelineService()
            pipeline.run_pipeline(doc_uuid, local_db)
        finally:
            local_db.close()

    background_tasks.add_task(run_sync_pipeline, document_id)
    logger.info(f"Dispatched document {document_id} to background processing.")



@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for asynchronous processing",
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or image file (JPG, PNG)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Uploads a PDF, JPG, or PNG document and registers a background processing job."""
    document = DocumentService.create_document(
        db=db,
        user=current_user,
        file_obj=file.file,
        filename=file.filename or "uploaded_file",
        storage_service=storage_service,
    )

    document.processing_status = "QUEUED"
    db.commit()

    # Dispatch to async worker / background task
    _dispatch_processing(document.id, background_tasks, db)

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        processing_status=document.processing_status,
        processing_stage=document.processing_stage,
        message="Document uploaded successfully and queued for extraction.",
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-trigger pipeline processing for a document",
)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-runs extraction pipeline for an existing document."""
    document = DocumentService.get_document_by_id(db=db, document_id=document_id, user=current_user)
    document.processing_status = "QUEUED"
    document.processing_stage = "INIT"
    db.commit()

    _dispatch_processing(document.id, background_tasks, db)

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        processing_status=document.processing_status,
        processing_stage=document.processing_stage,
        message="Document reprocessing queued successfully.",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List uploaded documents for the current user",
)
def list_documents(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by processing status"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a paginated list of documents owned by the authenticated user."""
    items, total = DocumentService.list_user_documents(
        db=db,
        user=current_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(total=total, items=items)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document processing status and metrics",
)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches details, processing status, stage, and counts for a specific document."""
    document = DocumentService.get_document_by_id(db=db, document_id=document_id, user=current_user)
    
    return DocumentDetailResponse(
        id=document.id,
        user_id=document.user_id,
        filename=document.filename,
        mime_type=document.mime_type,
        file_size_bytes=document.file_size_bytes,
        page_count=document.page_count,
        processing_status=document.processing_status,
        processing_stage=document.processing_stage,
        overall_confidence=document.overall_confidence,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        questions_count=len(document.questions),
        pages_count=len(document.pages),
        review_items_count=len(document.review_items),
        answer_keys_count=len(document.answer_keys),
    )


@router.get(
    "/{document_id}/pages",
    response_model=List[PageResponse],
    summary="Get normalized page content for a document",
)
def get_document_pages(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all normalized pages extracted from the document."""
    pages = DocumentService.get_document_pages(db=db, document_id=document_id, user=current_user)
    return pages


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all extracted data",
)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Deletes a document and cascades deletion to all questions, pages, and review items."""
    DocumentService.delete_document(
        db=db, document_id=document_id, user=current_user, storage_service=storage_service
    )
    return None
