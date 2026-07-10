"""resize chunk embedding to 1536 dims for OpenAI text-embedding-3-small

Switches the active embedding model from Gemini (768) to OpenAI (1536). Vectors
of different dimensions live in different spaces and cannot be cast, so this
migration DROPS all existing chunk embeddings and resets their parent documents
to 'pending' so they get re-embedded by the worker under the new provider.

Sequence: drop HNSW index -> clear chunks -> alter column type -> reset docs ->
recreate HNSW index. (An ANN index can't exist across the ALTER, and the column
can't be resized while rows hold 768-dim data.)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-07

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_DIM = 1536  # OpenAI text-embedding-3-small native dimension
OLD_DIM = 768  # Gemini gemini-embedding-001


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")

    # Existing 768-dim vectors are invalid at 1536 and can't be cast. Remove
    # them; the documents they belong to are reset to 'pending' below so the
    # ingestion worker re-embeds them under the new provider.
    op.execute("TRUNCATE TABLE document_chunks")

    # USING ... ::vector(1536) satisfies the type change on the now-empty table.
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ALTER COLUMN embedding TYPE vector({NEW_DIM}) "
        f"USING embedding::vector({NEW_DIM})"
    )

    # Any previously-ingested doc must be re-processed; clear stale provenance.
    op.execute(
        "UPDATE documents SET status = 'pending', error = NULL, "
        "embedding_provider = NULL, embedding_model = NULL "
        "WHERE status = 'ready'"
    )

    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.execute("TRUNCATE TABLE document_chunks")
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ALTER COLUMN embedding TYPE vector({OLD_DIM}) "
        f"USING embedding::vector({OLD_DIM})"
    )
    op.execute(
        "UPDATE documents SET status = 'pending', error = NULL, "
        "embedding_provider = NULL, embedding_model = NULL "
        "WHERE status = 'ready'"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )
