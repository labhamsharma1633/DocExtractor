import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.page import DocumentPage
    from app.db.models.question import Question
    from app.db.models.answer_key import AnswerKey
    from app.db.models.review_item import ReviewItem
    from app.db.models.relationship import DocumentRelationship


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status tracking
    processing_status: Mapped[str] = mapped_column(
        String(50), default="UPLOADED", index=True, nullable=False
    )  # UPLOADED, QUEUED, PROCESSING, COMPLETED, PARTIAL, FAILED
    processing_stage: Mapped[str] = mapped_column(
        String(50), default="INIT", nullable=False
    )  # INIT, OCR_PROCESSING, QUESTION_EXTRACTION, ANSWER_MATCHING, VALIDATION, COMPLETED
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="document", cascade="all, delete-orphan"
    )
    answer_keys: Mapped[List["AnswerKey"]] = relationship(
        "AnswerKey", back_populates="document", cascade="all, delete-orphan"
    )
    review_items: Mapped[List["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="document", cascade="all, delete-orphan"
    )
    relationships_as_source: Mapped[List["DocumentRelationship"]] = relationship(
        "DocumentRelationship",
        foreign_keys="DocumentRelationship.source_document_id",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    relationships_as_target: Mapped[List["DocumentRelationship"]] = relationship(
        "DocumentRelationship",
        foreign_keys="DocumentRelationship.related_document_id",
        back_populates="related_document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.processing_status}>"
