"""Vector similarity search over ingested document chunks (the RAG retriever)."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import get_embedding_provider
from app.models.document import Document, DocumentChunk
from app.schemas.document import SearchHit


async def search_documents(
    db: AsyncSession,
    query: str,
    k: int = 5,
) -> list[SearchHit]:
    """Embed ``query`` and return the ``k`` nearest chunks by cosine distance.

    Returned hits carry a cosine *similarity* score (1 - distance), so higher is
    a closer match.
    """
    if not query.strip():
        return []
    k = max(1, min(k, 50))

    provider = get_embedding_provider()
    # The provider SDK call is blocking; keep it off the event loop.
    query_vec = await asyncio.to_thread(provider.embed_query, query)

    distance = DocumentChunk.embedding.cosine_distance(query_vec)
    stmt = (
        select(
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            Document.filename,
            distance.label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .order_by(distance)
        .limit(k)
    )
    result = await db.execute(stmt)

    return [
        SearchHit(
            document_id=row.document_id,
            filename=row.filename,
            chunk_index=row.chunk_index,
            content=row.content,
            score=1.0 - float(row.distance),
        )
        for row in result
    ]
