import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document import Document


class AnswerKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "answer_keys"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    raw_key_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parsed_answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="answer_keys")

    def __repr__(self) -> str:
        return f"<AnswerKey id={self.id} doc_id={self.document_id} answers_count={len(self.parsed_answers)}>"
