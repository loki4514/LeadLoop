import logging
import math
import re
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger("embeddings.gemini")


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embeddings via the google-genai SDK.

    Uses asymmetric task types — documents and queries are embedded with
    different ``task_type`` hints, which improves retrieval quality.

    The output dimension is pinned to ``dim`` via ``output_dimensionality`` so
    it matches the pgvector column. Note: gemini-embedding models only return
    pre-normalized vectors at their native (max) dimension; at any smaller dim
    we must normalize ourselves for cosine similarity to be meaningful.
    """

    name = "gemini"

    def __init__(self, api_key: str, model: str, dim: int):
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY is required for the gemini provider")
        self.model = model
        self.dim = dim
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]

    # Gemini's batchEmbedContents accepts at most 100 items per request, so
    # larger documents must be embedded in sub-batches and concatenated in order.
    _MAX_BATCH = 100
    # Bounded in-provider retries for 429s, honoring the server's retry delay.
    _MAX_429_RETRIES = 6
    _DEFAULT_RETRY_WAIT = 30.0  # seconds, if the 429 gives no retryDelay

    @staticmethod
    def _retry_after_seconds(err: ClientError) -> float | None:
        """Parse the retry delay Gemini returns on a 429 (e.g. 'Please retry in
        52.19s' or a RetryInfo '52s'). Returns None if not present."""
        msg = str(err)
        m = re.search(r"retry in\s+([\d.]+)s", msg, re.IGNORECASE)
        if not m:
            m = re.search(r"'retryDelay':\s*'(\d+)s'", msg)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    def _embed_batch(self, batch: list[str], task_type: str) -> list[list[float]]:
        """Embed one <=100-item batch, waiting out 429 rate limits."""
        for attempt in range(self._MAX_429_RETRIES + 1):
            try:
                resp = self._client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.dim,
                    ),
                )
                return [self._normalize(list(e.values)) for e in resp.embeddings]
            except ClientError as err:
                if err.code != 429 or attempt == self._MAX_429_RETRIES:
                    raise
                wait = self._retry_after_seconds(err) or self._DEFAULT_RETRY_WAIT
                # Small cushion so we don't retry a hair too early.
                wait += 1.0
                logger.warning(
                    "gemini embed rate-limited (429); waiting %.1fs then retrying "
                    "(attempt %d/%d)",
                    wait,
                    attempt + 1,
                    self._MAX_429_RETRIES,
                )
                time.sleep(wait)
        # Unreachable: loop either returns or raises.
        raise RuntimeError("embed retry loop exited unexpectedly")

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._MAX_BATCH):
            batch = texts[start : start + self._MAX_BATCH]
            vectors.extend(self._embed_batch(batch, task_type))
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]
