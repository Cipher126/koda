import os
from typing import Any
from google import genai
from google.genai import types
from agent.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """
    Google Gemini provider implementation.
    Uses the new google-genai SDK.
    """

    AVAILABLE_MODELS = [
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.1-pro-preview",
    ]

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str = None):
        super().__init__(model, api_key)

        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY in your .env file.")

        self.client = genai.Client(api_key=resolved_key)

    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        Send messages to Gemini and return a standardized response.
        """
        system_instruction = None
        conversation = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                conversation.append(msg)

        gemini_messages = self._convert_messages(conversation)

        # Convert tools if provided
        gemini_tools = self._convert_tools(tools) if tools else None

        # Build config
        config_kwargs = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if gemini_tools:
            config_kwargs["tools"] = gemini_tools

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        response = self.client.models.generate_content(
            model=self.model,
            contents=gemini_messages,
            config=config
        )

        return self._parse_response(response)

    def get_available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS


    def _convert_messages(self, messages: list[dict]) -> list[types.Content]:
        """
        Convert our standard message format to Gemini Content objects.

        Our format:     {"role": "user", "content": "hello"}
        Gemini format:  types.Content(role="user", parts=[types.Part(text="hello")])
        """
        converted = []
        for msg in messages:
            role = msg["role"]

            if role == "assistant":
                role = "model"

            if role == "tool":
                converted.append(types.Content(
                    role="user",
                    parts=[types.Part(text=f"Tool result: {msg['content']}")]
                ))
                continue

            converted.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))

        return converted

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """
        Convert our standard tool definitions to Gemini Tool objects.
        """
        declarations = []
        for tool in tools:
            declarations.append(types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool.get("parameters", {})
            ))
        return [types.Tool(function_declarations=declarations)]

    def _parse_response(self, response) -> dict:
        result = {"content": None, "tool_calls": [], "usage": None}

        try:
            if not response or not response.candidates:
                result["content"] = "Error: Empty response from Gemini."
                return result

            candidate = response.candidates[0]

            if not candidate.content or not candidate.content.parts:
                return result

            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    result["tool_calls"].append({
                        "id": f"call_{part.function_call.name}",
                        "name": part.function_call.name,
                        "arguments": dict(part.function_call.args)
                    })
                elif hasattr(part, "text") and part.text:
                    result["content"] = part.text

            # Extract token usage
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                result["usage"] = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }

        except Exception as e:
            result["content"] = f"Error parsing Gemini response: {e}"

        return result