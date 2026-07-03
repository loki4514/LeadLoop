from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.enums import DocumentStatus, pg_enum


class Document(Base, TimestampMixin):
    """A source file uploaded for the RAG knowledge base (pdf/docx/xlsx/txt).

    The raw file lives on disk (``storage_path``); its extracted+embedded
    chunks live in ``document_chunks``.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    # Path on the shared uploads volume.
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        pg_enum(DocumentStatus, "document_status"),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)

    # Which provider/model produced the stored chunk embeddings. Lets us detect
    # when a document predates a provider switch and needs re-embedding.
    embedding_provider: Mapped[str | None] = mapped_column(String(64))
    embedding_model: Mapped[str | None] = mapped_column(String(128))

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentChunk(Base, TimestampMixin):
    """One embedded slice of a document's markdown, for vector retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Dimension is fixed to the active embedding model (see settings/migration).
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.EMBEDDING_DIM), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")
