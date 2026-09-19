import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document import Document


class DocumentRelationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_relationships"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    related_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), default="ANSWER_KEY", nullable=False
    )  # ANSWER_KEY, RELATED_DOCUMENT, SOURCE_DOCUMENT

    # Relationships
    source_document: Mapped["Document"] = relationship(
        "Document", foreign_keys=[source_document_id], back_populates="relationships_as_source"
    )
    related_document: Mapped["Document"] = relationship(
        "Document", foreign_keys=[related_document_id], back_populates="relationships_as_target"
    )

    def __repr__(self) -> str:
        return f"<DocumentRelationship source={self.source_document_id} related={self.related_document_id} type={self.relationship_type}>"
