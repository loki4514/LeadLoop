from google import genai
from google.genai import types

from app.llm.base import ChatLLM


class GeminiChatLLM(ChatLLM):
    """Google Gemini text generation via the google-genai SDK.

    Uses the same SDK as the embedding provider. The system instruction is
    passed via ``GenerateContentConfig`` so it is handled as a first-class
    system prompt rather than prepended to the user turn.
    """

    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("LLM_API_KEY (or EMBEDDING_API_KEY) is required for gemini chat")
        self.model = model
        self._client = genai.Client(api_key=api_key)

    def generate(self, system: str, prompt: str) -> str:
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,  # grounded, low-invention answers
            ),
        )
        return (resp.text or "").strip()
