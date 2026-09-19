import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.option import OptionResponse


class ImageRefSchema(BaseModel):
    page: int
    path: str
    bbox: Optional[List[float]] = None


class TableRefSchema(BaseModel):
    headers: List[str]
    rows: List[List[str]]
    image_crop_path: Optional[str] = None


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    question_number: Optional[str] = None
    question_text: str
    question_type: str
    confidence_score: float
    extraction_status: str
    matched_answer: Optional[str] = None
    answer_source: Optional[str] = None
    image_url: Optional[str] = None
    options: List[OptionResponse] = []

    context: Optional[str] = None
    context_type: Optional[str] = None
    images: List[ImageRefSchema] = []
    tables: List[TableRefSchema] = []
    requires_visual_context: bool = False
    review_required: bool = False
    warnings: List[str] = []

    source_pages: List[int] = []
    created_at: datetime
    updated_at: datetime


class QuestionListResponse(BaseModel):
    total: int
    items: List[QuestionResponse]


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    matched_answer: Optional[str] = None
    context: Optional[str] = None

