"""documents + pgvector chunk store

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Keep in sync with settings.EMBEDDING_DIM and the active embedding model.
# Switching to a model with a different dimension needs a new migration that
# alters this column and a re-embed of all chunks.
EMBEDDING_DIM = 768

# Single source of truth for the enum type. create_table() below emits the
# CREATE TYPE exactly once; we do NOT also call .create() (doing both is what
# triggers DuplicateObject). Guard with a manual existence check in upgrade()
# so re-runs after a partial failure stay clean.
document_status_enum = sa.Enum(
    "pending", "processing", "ready", "failed", name="document_status"
)


def upgrade() -> None:
    # pgvector extension must exist before we can declare a vector column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("embedding_provider", sa.String(64), nullable=True),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(EMBEDDING_DIM),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"]
    )

    # Approximate-nearest-neighbour index for cosine distance (<=>).
    # HNSW (not ivfflat): correct from the first row, no lists/probes tuning,
    # and high recall as the corpus grows. ivfflat only probes a subset of
    # clusters by default and silently under-returns on small/sparse data.
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    document_status_enum.drop(op.get_bind(), checkfirst=True)
