import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class RelationshipCreate(BaseModel):
    related_document_id: uuid.UUID
    relationship_type: str = "ANSWER_KEY"  # ANSWER_KEY, RELATED_DOCUMENT, SOURCE_DOCUMENT


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_document_id: uuid.UUID
    related_document_id: uuid.UUID
    relationship_type: str
    created_at: datetime


class RelationshipListResponse(BaseModel):
    total: int
    items: List[RelationshipResponse]
