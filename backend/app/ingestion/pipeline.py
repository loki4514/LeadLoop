"""End-to-end ingestion: file -> markdown -> chunks -> embeddings -> pgvector.

This is the unit of work the RQ worker runs. It is synchronous on purpose
(RQ jobs are sync) and uses the sync DB session.
"""
import logging

from app.core.config import settings
from app.db.sync_session import SyncSessionLocal
from app.embeddings import get_embedding_provider
from app.ingestion.chunking import chunk_text
from app.ingestion.extract import extract_markdown
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus

logger = logging.getLogger("ingestion")


def ingest_document(document_id: int) -> None:
    """Process one uploaded document. Safe to retry: clears prior chunks first."""
    session = SyncSessionLocal()
    try:
        doc = session.get(Document, document_id)
        if doc is None:
            logger.warning("ingest_document: document %s not found", document_id)
            return

        doc.status = DocumentStatus.PROCESSING
        doc.error = None
        session.commit()

        try:
            markdown = extract_markdown(doc.storage_path)
            chunks = chunk_text(
                markdown,
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )
            if not chunks:
                raise ValueError("no extractable text content")

            provider = get_embedding_provider()
            vectors = provider.embed_documents(chunks)
            if len(vectors) != len(chunks):
                raise RuntimeError(
                    f"embedding count {len(vectors)} != chunk count {len(chunks)}"
                )

            # Re-ingestion: drop any stale chunks before inserting fresh ones.
            session.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).delete()

            for idx, (content, embedding) in enumerate(zip(chunks, vectors)):
                session.add(
                    DocumentChunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        content=content,
                        embedding=embedding,
                    )
                )

            doc.embedding_provider = provider.name
            doc.embedding_model = provider.model
            doc.status = DocumentStatus.READY
            session.commit()
            logger.info(
                "ingested document %s: %d chunks (%s/%s)",
                doc.id,
                len(chunks),
                provider.name,
                provider.model,
            )
        except Exception as exc:  # noqa: BLE001 - record failure, don't crash worker
            session.rollback()
            doc = session.get(Document, document_id)
            if doc is not None:
                doc.status = DocumentStatus.FAILED
                doc.error = str(exc)[:2000]
                session.commit()
            logger.exception("ingestion failed for document %s", document_id)
            raise
    finally:
        session.close()
