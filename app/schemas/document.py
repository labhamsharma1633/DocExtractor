import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    processing_status: str
    processing_stage: str
    overall_confidence: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    questions_count: int = 0
    pages_count: int = 0
    review_items_count: int = 0
    answer_keys_count: int = 0


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    processing_status: str
    processing_stage: str
    message: str
