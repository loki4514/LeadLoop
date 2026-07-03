"""Celery wrapper around the document ingestion pipeline.

The heavy lifting lives in ``app.ingestion.pipeline.ingest_document`` (a plain
sync function, framework-agnostic). This task just adapts it to Celery and adds
bounded retries for transient failures (e.g. the embedding API being briefly
unavailable). The pipeline itself records permanent failures on the Document
row, so we only retry, not swallow.
"""
import logging

from app.core.celery_app import celery_app
from app.ingestion.pipeline import ingest_document as _ingest_document

logger = logging.getLogger("tasks.ingestion")


@celery_app.task(
    name="app.tasks.ingestion.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # seconds; backoff handled below
    acks_late=True,
)
def ingest_document(self, document_id: int) -> None:
    """Ingest one uploaded document into pgvector.

    On failure the pipeline marks the Document as FAILED with an error message,
    then re-raises so Celery can retry with exponential backoff.
    """
    try:
        _ingest_document(document_id)
    except Exception as exc:  # noqa: BLE001 - retry transient failures
        logger.warning(
            "ingest_document(%s) failed (attempt %s/%s): %s",
            document_id,
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        # Exponential backoff: 30s, 60s, 120s.
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))
