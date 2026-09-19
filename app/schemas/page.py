import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    extracted_text: str
    ocr_used: bool
    ocr_confidence: Optional[float] = None
    image_path: Optional[str] = None
    rotation: int = 0
    page_metadata: Optional[dict] = None
    created_at: datetime


class PageContent(BaseModel):
    """Normalized in-memory page data structure passed through extraction pipelines."""
    document_id: uuid.UUID
    page_number: int
    extracted_text: str
    ocr_used: bool
    ocr_confidence: Optional[float] = None
    image_path: Optional[str] = None
    rotation: int = 0
    page_metadata: Optional[dict] = None
