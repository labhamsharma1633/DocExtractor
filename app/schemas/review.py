import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    question_id: Optional[uuid.UUID] = None
    review_type: str
    severity: str
    message: str
    confidence: Optional[float] = None
    is_resolved: bool
    created_at: datetime


class ReviewItemListResponse(BaseModel):
    total: int
    items: List[ReviewItemResponse]
