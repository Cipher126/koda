import os
import json
from openai import OpenAI
from agent.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation.
    Also supports any OpenAI-compatible API (Groq, xAI/Grok etc.)
    by passing a custom base_url.
    """

    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]

    # OpenAI-compatible endpoints for other providers
    COMPATIBLE_ENDPOINTS = {
        "groq": "https://api.groq.com/openai/v1",
        "grok": "https://api.x.ai/v1",
    }

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = None,
        base_url: str = None,
        provider_name: str = "openai"
    ):
        super().__init__(model, api_key)

        self.provider_name = provider_name

        # Resolve API key based on provider
        resolved_key = api_key or self._resolve_api_key(provider_name)
        if not resolved_key:
            raise ValueError(
                f"API key not found for '{provider_name}'. "
                f"Set the appropriate key in your .env file."
            )

        resolved_url = base_url or self.COMPATIBLE_ENDPOINTS.get(provider_name)

        self.client = OpenAI(
            api_key=resolved_key,
            base_url=resolved_url
        )

    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Send messages to OpenAI (or compatible API) and return standardized response.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,  # OpenAI format is our standard format
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    def get_available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS

    def _resolve_api_key(self, provider_name: str) -> str:
        """
        Load the right API key from .env based on provider name.

        openai  → OPENAI_API_KEY
        groq    → GROQ_API_KEY
        grok    → XAI_API_KEY
        """
        key_map = {
            "openai": "OPENAI_API_KEY",
            "groq":   "GROQ_API_KEY",
            "grok":   "XAI_API_KEY",
        }
        env_key = key_map.get(provider_name)
        return os.getenv(env_key) if env_key else None

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """
        Convert our standard tool definitions to OpenAI format.
        Identical to Groq's format.
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

    def _parse_response(self, response) -> dict:
        """
        Convert OpenAI's response to our standard format.
        Identical to Groq's parsing logic.
        """
        result = {"content": None, "tool_calls": []}

        message = response.choices[0].message

        if message.content:
            result["content"] = message.content

        if message.tool_calls:
            for tool_call in message.tool_calls:
                result["tool_calls"].append({
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                })

        if hasattr(response, "usage") and response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return result