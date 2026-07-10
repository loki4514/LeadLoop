from openai import OpenAI

from app.llm.base import ChatLLM


class OpenAIChatLLM(ChatLLM):
    """OpenAI chat completions via the official openai SDK.

    ``base_url`` is configurable, so this adapter also works against any
    OpenAI-compatible endpoint (Azure OpenAI, a local vLLM/Ollama server, etc.)
    without code changes — set OPENAI_BASE_URL.
    """

    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai chat provider")
        self.model = model
        # Only pass base_url when explicitly set. Passing base_url=None (or "")
        # does NOT fall back to the default endpoint in the openai SDK — it
        # yields an empty base URL and httpx raises UnsupportedProtocol.
        kwargs = {"base_url": base_url} if base_url else {}
        self._client = OpenAI(api_key=api_key, **kwargs)

    def generate(self, system: str, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,  # grounded, low-invention answers
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
