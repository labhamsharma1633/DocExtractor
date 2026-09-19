import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    option_key: str
    option_text: str
    is_correct: Optional[bool] = None
    order_index: int


class OptionCreate(BaseModel):
    option_key: str
    option_text: str
    is_correct: Optional[bool] = None
    order_index: int = 0
