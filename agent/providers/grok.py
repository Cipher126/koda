import os
from agent.providers.openai import OpenAIProvider


class GrokProvider(OpenAIProvider):
    """
    xAI Grok provider.
    Inherits from OpenAIProvider since xAI's API is OpenAI-compatible.
    Just points to a different base_url and uses XAI_API_KEY.
    """

    AVAILABLE_MODELS = [
        "grok-4-1-fast-reasoning",
        "grok-4.20-multi-agent-beta-0309",
        "grok-4.20-beta-0309-reasoning",
        "grok-code-fast-1",
    ]

    XAI_BASE_URL = "https://api.x.ai/v1"

    def __init__(self, model: str = "grok-3-mini", api_key: str = None):
        # Resolve API key
        resolved_key = api_key or os.getenv("XAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "xAI API key not found. Set XAI_API_KEY in your .env file."
            )

        # Initialize OpenAIProvider with xAI's endpoint
        super().__init__(
            model=model,
            api_key=resolved_key,
            base_url=self.XAI_BASE_URL,
            provider_name="grok"
        )

    def get_available_models(self) -> list[str]:
        # Override to return Grok's models instead of OpenAI's
        return self.AVAILABLE_MODELS