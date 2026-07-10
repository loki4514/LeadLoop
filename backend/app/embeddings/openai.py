import math

from openai import OpenAI

from app.embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text embeddings via the official openai SDK.

    ``base_url`` is configurable, so this also works against any
    OpenAI-compatible embeddings server (set OPENAI_BASE_URL).

    Dimension note: text-embedding-3-* models default to 1536 (small) / 3072
    (large) but accept a ``dimensions`` param to shorten the output. We pass
    ``dim`` so the vector matches the pgvector column — but the column must be
    sized to that dim (see EMBEDDING_DIM / the migration). Switching the active
    embedder from Gemini (768) to OpenAI requires a dimension migration + a full
    re-embed of existing documents.
    """

    name = "openai"

    def __init__(self, api_key: str, model: str, dim: int, base_url: str | None = None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai embedding provider")
        self.model = model
        self.dim = dim
        # Only pass base_url when explicitly set. Passing base_url=None (or "")
        # does NOT fall back to the default endpoint in the openai SDK — it
        # yields an empty base URL and httpx raises UnsupportedProtocol.
        kwargs = {"base_url": base_url} if base_url else {}
        self._client = OpenAI(api_key=api_key, **kwargs)

    # OpenAI allows large batches, but cap conservatively to bound request size.
    _MAX_BATCH = 100

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._MAX_BATCH):
            batch = texts[start : start + self._MAX_BATCH]
            resp = self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dim,
            )
            # API returns items with an `index`; sort to guarantee input order.
            ordered = sorted(resp.data, key=lambda d: d.index)
            vectors.extend(self._normalize(list(d.embedding)) for d in ordered)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]
