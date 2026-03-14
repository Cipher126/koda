import json
import httpx
from agent.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    """
    Ollama provider for locally running LLMs.
    No API key required — models run on your machine.

    Requires Ollama to be installed and running:
    https://ollama.com

    Pull a model before using:
        ollama pull llama3
        ollama pull codellama
        ollama pull mistral
    """

    # Fallback list if Ollama server is unreachable
    POPULAR_MODELS = [
        "llama3",
        "llama3:8b",
        "llama3:70b",
        "codellama",
        "mistral",
        "gemma2",
        "phi3",
    ]

    def __init__(
        self,
        model: str = "llama3",
        api_key: str = None,
        base_url: str = "http://localhost:11434"
    ):
        super().__init__(model, api_key)
        self.base_url = base_url

        self.http_client = httpx.Client(base_url=self.base_url, timeout=120.0)


    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Send messages to local Ollama instance and return standardized response.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        if tools:
            payload["tools"] = self._convert_tools(tools)

        response = self.http_client.post("/api/chat", json=payload)
        response.raise_for_status()

        return self._parse_response(response.json())

    def get_available_models(self) -> list[str]:
        """
        Query the local Ollama server for installed models.
        Falls back to POPULAR_MODELS if server is unreachable.
        """
        try:
            response = self.http_client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

            # Extract model names from response
            return [model["name"] for model in data.get("models", [])]

        except Exception:
            # Ollama not running or unreachable — return popular models as suggestion
            return self.POPULAR_MODELS

    def is_available(self) -> bool:
        """
        Check if Ollama is running on this machine.
        Useful to show a helpful error before trying to chat.
        """
        try:
            response = self.http_client.get("/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """
        Convert our standard tool definitions to Ollama's format.
        Same as OpenAI/Groq format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {})
                }
            }
            for tool in tools
        ]

    def _parse_response(self, response: dict) -> dict:
        """
        Convert Ollama's response to our standard format.
        """
        result = {"content": None, "tool_calls": []}

        message = response.get("message", {})

        # Extract text content
        if message.get("content"):
            result["content"] = message["content"]

        # Extract tool calls if present
        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func = tool_call.get("function", {})
                arguments = func.get("arguments", {})

                # Ollama may return arguments as string or dict
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                result["tool_calls"].append({
                    "name": func.get("name"),
                    "arguments": arguments
                })

        return result

    def __del__(self):
        """Clean up the HTTP client when provider is destroyed."""
        try:
            self.http_client.close()
        except Exception:
            pass