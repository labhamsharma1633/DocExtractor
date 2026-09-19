import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AnswerKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    raw_key_text: str
    parsed_answers: Dict[str, str]
    page_number: Optional[int] = None
    created_at: datetime


class AnswerKeyListResponse(BaseModel):
    total: int
    items: List[AnswerKeyResponse]
