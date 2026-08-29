import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee
from app.core.storage import save_upload
from app.db.session import get_db
from app.models.document import Document
from app.models.employee import Employee
from app.models.enums import DocumentStatus
from app.retrieval import search_documents
from app.schemas.document import DocumentRead, SearchResponse

router = APIRouter(prefix="/documents", tags=["documents"])

# MarkItDown handles more, but we gate uploads to the formats we expect.
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".csv"}


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_employee)],
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file, persist it, and enqueue it for ingestion into pgvector."""
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type {ext!r}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    stored_name = f"{uuid.uuid4().hex}{ext}"

    # SpooledTemporaryFile keeps small uploads in memory and spills large ones to
    # disk, so this streams either way. save_upload() then writes it to the
    # bucket (prod) or UPLOAD_DIR (dev) and returns the storage_path to record.
    await file.seek(0)
    storage_path = save_upload(file.file, stored_name)

    doc = Document(
        filename=filename,
        content_type=file.content_type,
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Hand off to the Celery worker; ingestion runs out of the request path.
    from app.tasks.ingestion import ingest_document as ingest_task

    ingest_task.delay(doc.id)

    return doc


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    k: int = 5,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    """Vector similarity search over ingested document chunks."""
    hits = await search_documents(db, q, k=k)
    return SearchResponse(query=q, hits=hits)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return doc
