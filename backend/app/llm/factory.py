from functools import lru_cache

from app.core.config import settings
from app.llm.base import ChatLLM

# Register chat providers here, mirroring app.embeddings.factory. To add another
# provider, implement ChatLLM in a new module and add a builder entry.
_BUILDERS = {}

# Per-provider fallback chat model, used when LLM_MODEL is left at its default
# (a Gemini name) but a different provider is selected. An explicit LLM_MODEL
# always wins.
_DEFAULT_MODEL = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}
# The shipped default of LLM_MODEL; if unchanged we treat it as "not set" so a
# provider switch can pick its own default rather than sending a Gemini model
# name to OpenAI.
_SHIPPED_LLM_MODEL_DEFAULT = "gemini-2.0-flash"


def _model_for(provider: str) -> str:
    if settings.LLM_MODEL and settings.LLM_MODEL != _SHIPPED_LLM_MODEL_DEFAULT:
        return settings.LLM_MODEL
    return _DEFAULT_MODEL.get(provider, settings.LLM_MODEL)


def _build_gemini() -> ChatLLM:
    from app.llm.gemini import GeminiChatLLM

    return GeminiChatLLM(api_key=settings.llm_api_key, model=_model_for("gemini"))


def _build_openai() -> ChatLLM:
    from app.llm.openai import OpenAIChatLLM

    return OpenAIChatLLM(
        api_key=settings.OPENAI_API_KEY,
        model=_model_for("openai"),
        base_url=settings.OPENAI_BASE_URL or None,
    )


_BUILDERS["gemini"] = _build_gemini
_BUILDERS["openai"] = _build_openai


@lru_cache
def get_chat_llm() -> ChatLLM:
    """Return the active chat LLM, selected by LLM_PROVIDER (gemini | openai)."""
    key = settings.LLM_PROVIDER.lower().strip()
    builder = _BUILDERS.get(key)
    if builder is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER={key!r}. Known: {sorted(_BUILDERS)}"
        )
    return builder()
