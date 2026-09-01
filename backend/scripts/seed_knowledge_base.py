"""Seed the RAG knowledge base from ``knowledge_base/`` so the demo chat has
real content to answer from.

Idempotent: a file already present as a READY document is skipped, so reruns are
cheap and won't re-embed (embeddings cost money). Pass ``--force`` to re-ingest
everything anyway — useful after editing a source file or switching embedding
providers.

Ingestion runs inline (not via the Celery worker) so the script exits only once
the chunks are actually queryable.

Run inside the backend container:
    python -m scripts.seed_knowledge_base
    python -m scripts.seed_knowledge_base --force
"""
import argparse
import os
import sys
import uuid

from sqlalchemy import select

from app.core.storage import save_upload
from app.db.sync_session import SyncSessionLocal
from app.ingestion.pipeline import ingest_document
from app.models.document import Document
from app.models.enums import DocumentStatus

# In the container the docker build context is ./backend, so repo-root's
# knowledge_base/ isn't in the image — compose mounts it at /knowledge_base
# instead. Outside the container, fall back to the repo-root directory
# (this file lives at repo-root/backend/scripts/). KB_DIR overrides both.
_REPO_KB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge_base",
)
KB_DIR = os.environ.get("KB_DIR") or (
    "/knowledge_base" if os.path.isdir("/knowledge_base") else _REPO_KB
)

# Mirrors ALLOWED_EXTENSIONS on the upload route.
EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".csv"}

CONTENT_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _source_files() -> list[str]:
    if not os.path.isdir(KB_DIR):
        return []
    return sorted(
        os.path.join(KB_DIR, name)
        for name in os.listdir(KB_DIR)
        if os.path.splitext(name)[1].lower() in EXTENSIONS
    )


def _stage(session, path: str, force: bool) -> int | None:
    """Create (or reset) the Document row for ``path``; return its id, or None
    if it is already ingested and ``force`` is off."""
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()

    existing = session.execute(
        select(Document).where(Document.filename == filename)
    ).scalars().first()

    if existing is not None and not force:
        if existing.status == DocumentStatus.READY:
            print(f"  skip    {filename} (already ingested)")
            return None
        # A prior run failed or was interrupted — retry it rather than skipping.
        print(f"  retry   {filename} (status={existing.status.value})")
        return existing.id

    # Copy into the app's own storage so the ingest path is identical to an
    # upload's (and works when the worker's filesystem differs from ours).
    with open(path, "rb") as fh:
        storage_path = save_upload(fh, f"{uuid.uuid4().hex}{ext}")

    if existing is not None:
        existing.storage_path = storage_path
        existing.status = DocumentStatus.PENDING
        existing.error = None
        session.commit()
        print(f"  reseed  {filename}")
        return existing.id

    doc = Document(
        filename=filename,
        content_type=CONTENT_TYPES.get(ext),
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    print(f"  add     {filename}")
    return doc.id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-ingest files that are already READY (re-embeds; costs money)",
    )
    args = parser.parse_args()

    files = _source_files()
    if not files:
        print(f"No ingestable files found in {KB_DIR}")
        return 1

    print(f"Seeding knowledge base from {KB_DIR} ({len(files)} file(s))")

    session = SyncSessionLocal()
    try:
        pending = [
            doc_id
            for path in files
            if (doc_id := _stage(session, path, args.force)) is not None
        ]
    finally:
        session.close()

    if not pending:
        print("Nothing to ingest — knowledge base is up to date.")
        return 0

    # Inline rather than ingest_task.delay(): the script should not exit before
    # the content is queryable, and seeding shouldn't require a running worker.
    failed = 0
    for doc_id in pending:
        try:
            ingest_document(doc_id)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed += 1
            print(f"  FAILED  document {doc_id}: {exc}")

    print(f"Ingested {len(pending) - failed}/{len(pending)} document(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
