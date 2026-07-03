from abc import ABC, abstractmethod


class ChatLLM(ABC):
    """Provider-agnostic chat/generation interface.

    Mirrors ``app.embeddings.EmbeddingProvider``: the rest of the app (the chat
    endpoint) talks to this interface, never a vendor SDK directly. Swap the
    provider behind the factory without touching call sites.
    """

    #: Provider key, e.g. "gemini".
    name: str
    #: Model id, e.g. "gemini-2.0-flash".
    model: str

    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        """Return the model's completion for ``prompt`` under ``system``.

        Blocking. Call from a thread when invoked inside async code.
        """
