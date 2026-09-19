import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.question import Question


class QuestionSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "question_sources"

    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="sources")

    def __repr__(self) -> str:
        return f"<QuestionSource q_id={self.question_id} page={self.page_number}>"
