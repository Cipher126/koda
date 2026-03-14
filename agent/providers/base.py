from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Every provider (Gemini, Groq, OpenAI etc.) must inherit
    from this and implement all abstract methods.
    """

    def __init__(self, model: str, api_key: str = None):
        """
        Args:
            model: The specific model to use e.g. "gemini-1.5-flash"
            api_key: The API key for the provider (None for local models like Ollama)
        """
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Send a conversation history to the LLM and get a response.

        Args:
            messages: Full conversation history as a list of dicts
                      e.g. [{"role": "user", "content": "explain this code"}]
            tools: Optional list of tool definitions the LLM can call

        Returns:
            dict with keys:
                "content"   -> the text response (str or None)
                "tool_calls" -> list of tool calls the LLM wants to make (or empty list)
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """
        Return a list of models this provider supports.
        Used when the user wants to browse and select a model.
        """
        pass

    def format_tool_call_result(self, tool_name: str, result: Any) -> dict:
        """
        Format a tool result to send back to the LLM.
        This has a default implementation since the format
        is similar across most providers.
        """
        return {
            "role": "tool",
            "name": tool_name,
            "content": str(result)
        }

    def __repr__(self):
        return f"{self.__class__.__name__}(model={self.model})"