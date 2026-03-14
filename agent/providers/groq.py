import os
from groq import Groq
from agent.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    """
    Groq inference provider.
    Supports Llama, Mixtral, and Gemma models served via Groq's API.
    """

    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-4-scout-17b-16e-instruct",

        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"

        "moonshotai/kimi-k2-instruct-0905",
        "qwen/qwen3-32b"
    ]

    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str = None):
        super().__init__(model, api_key)

        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY in your .env file.")

        self.client = Groq(api_key=resolved_key)

    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            error_msg = str(e).lower()
            # If tool use failed, retry without tools
            if "tool_use_failed" in error_msg or "failed_generation" in error_msg:
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                response = self.client.chat.completions.create(**kwargs)
                return self._parse_response(response)
            raise

    def get_available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """
        Convert our standard tool definitions to Groq's format.
        Groq follows the OpenAI tool format exactly.

        Our format:
        {
            "name": "read_file",
            "description": "reads a file",
            "parameters": {...}
        }

        Groq/OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "reads a file",
                "parameters": {...}
            }
        }
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
        result = {"content": None, "tool_calls": []}

        if not response or not response.choices:
            return result

        message = response.choices[0].message

        if message.content:
            result["content"] = message.content

        if message.tool_calls:
            for tool_call in message.tool_calls:
                import json
                result["tool_calls"].append({
                    "id": tool_call.id,  # capture the ID
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                })

        return result
