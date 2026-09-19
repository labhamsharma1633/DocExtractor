import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.question import Question


class ReviewItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "review_items"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    review_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MISSING_OPTIONS, OCR_UNCERTAINTY, SPANNING_PAGES, BOUNDARY_UNCERTAIN, ANSWER_NOT_FOUND, ANSWER_MISMATCH, etc.
    severity: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", nullable=False
    )  # LOW, MEDIUM, HIGH, CRITICAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="review_items")
    question: Mapped[Optional["Question"]] = relationship("Question", back_populates="review_items")

    def __repr__(self) -> str:
        return f"<ReviewItem id={self.id} type={self.review_type} severity={self.severity} resolved={self.is_resolved}>"
