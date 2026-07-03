from functools import lru_cache

from app.core.config import settings
from app.llm.base import ChatLLM

# Register chat providers here, mirroring app.embeddings.factory. To add another
# provider, implement ChatLLM in a new module and add a builder entry.
_BUILDERS = {}


def _build_gemini() -> ChatLLM:
    from app.llm.gemini import GeminiChatLLM

    return GeminiChatLLM(api_key=settings.llm_api_key, model=settings.LLM_MODEL)


_BUILDERS["gemini"] = _build_gemini


@lru_cache
def get_chat_llm() -> ChatLLM:
    """Return the active chat LLM. Provider is inferred from the model name
    (only gemini is wired today, so we default to it)."""
    # Kept simple: one provider for now. Extend with an LLM_PROVIDER setting when
    # a second provider is added.
    return _BUILDERS["gemini"]()
