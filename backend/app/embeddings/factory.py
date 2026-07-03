from functools import lru_cache

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider

# Register providers here. Each value is a zero-arg-from-settings builder.
# To add OpenAI/DeepSeek/Voyage later: implement EmbeddingProvider in a new
# module and add a builder entry — no other code changes.
_BUILDERS = {}


def _build_gemini() -> EmbeddingProvider:
    from app.embeddings.gemini import GeminiEmbeddingProvider

    return GeminiEmbeddingProvider(
        api_key=settings.EMBEDDING_API_KEY,
        model=settings.EMBEDDING_MODEL,
        dim=settings.EMBEDDING_DIM,
    )


_BUILDERS["gemini"] = _build_gemini


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return the active embedding provider, selected by EMBEDDING_PROVIDER."""
    key = settings.EMBEDDING_PROVIDER.lower().strip()
    builder = _BUILDERS.get(key)
    if builder is None:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER={key!r}. "
            f"Known: {sorted(_BUILDERS)}"
        )
    provider = builder()
    if provider.dim != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Provider {key!r} dim={provider.dim} != EMBEDDING_DIM="
            f"{settings.EMBEDDING_DIM}. Update the setting and re-embed/migrate."
        )
    return provider
