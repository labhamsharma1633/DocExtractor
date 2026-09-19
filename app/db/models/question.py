import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.option import QuestionOption
    from app.db.models.source import QuestionSource
    from app.db.models.review_item import ReviewItem


class Question(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "questions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(50), default="MCQ", nullable=False
    )  # MCQ, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    extraction_status: Mapped[str] = mapped_column(
        String(50), default="EXTRACTED", nullable=False
    )  # EXTRACTED, PARTIAL, REVIEW
    matched_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # INTERNAL_KEY, EXTERNAL_DOC, MANUAL
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.order_index",
    )
    sources: Mapped[List["QuestionSource"]] = relationship(
        "QuestionSource",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionSource.page_number",
    )
    review_items: Mapped[List["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} num={self.question_number} type={self.question_type} conf={self.confidence_score}>"
