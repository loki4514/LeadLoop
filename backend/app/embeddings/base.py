from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-agnostic embedding interface.

    Every concrete provider (Gemini, OpenAI, Voyage, ...) implements this so the
    rest of the app — ingestion and retrieval — never imports a vendor SDK
    directly. Swap providers via the ``EMBEDDING_PROVIDER`` setting and the
    factory in ``app.embeddings.factory``.

    Note: ``dim`` is part of the contract because the pgvector column is sized
    to it. Switching to a provider with a different ``dim`` requires a migration
    and re-embedding existing documents.
    """

    #: Human-readable provider key, e.g. "gemini". Stored on documents so we can
    #: detect rows that predate a provider switch.
    name: str
    #: The embedding model id, e.g. "text-embedding-004".
    model: str
    #: Output vector dimension. Must match settings.EMBEDDING_DIM / the column.
    dim: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for storage. Order matches input."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for similarity search."""
