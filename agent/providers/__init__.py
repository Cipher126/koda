import random
import time

from agent.providers.gemini import GeminiProvider
from agent.providers.groq import GroqProvider
from agent.providers.openai import OpenAIProvider
from agent.providers.grok import GrokProvider
from agent.providers.ollama import OllamaProvider


PROVIDER_MAP = {
    "gemini": GeminiProvider,
    "groq":   GroqProvider,
    "openai": OpenAIProvider,
    "grok":   GrokProvider,
    "ollama": OllamaProvider,
}

# Maps model name → provider name
# So the user can say --model llama-3.3-70b and we know to use Groq
MODEL_TO_PROVIDER = {
    # Gemini models
    "gemini-2.5-pro": "gemini",
    "gemini-2.5-flash-lite": "gemini",
    "gemini-2.5-flash": "gemini",
    "gemini-3.1-pro-preview": "gemini",

    # Groq models (Llama, Mixtral, moonshot via Groq)
    "llama-3.3-70b-versatile": "groq",
    "llama-3.1-8b-instant": "groq",
    "meta-llama/llama-4-scout-17b-16e-instruct": "groq",
    "openai/gpt-oss-120b": "groq",
    "moonshotai/kimi-k2-instruct-0905": "groq",
    "qwen/qwen3-32b": "groq",

    # OpenAI models
    "gpt-5o":        "openai",
    "gpt-5-mini":   "openai",
    "gpt-5.1":   "openai",

    # Grok models
    "grok-4-1-fast-reasoning": "grok",
    "grok-4.20-multi-agent-beta-0309": "grok",
    "grok-4.20-beta-0309-reasoning": "grok",
    "grok-code-fast-1": "grok",

    # Ollama models (locally installed)
    "llama3":     "ollama",
    "codellama":  "ollama",
    "mistral":    "ollama",
    "gemma2":     "ollama",
    "phi3":       "ollama",
}

PROVIDER_DEFAULTS = {
    "groq":   "moonshotai/kimi-k2-instruct-0905",
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "grok":   "grok-4-1-fast-reasoning",
    "ollama": "llama3",
}

# Default provider and model if user doesn't specify
DEFAULT_PROVIDER = "groq"
DEFAULT_MODEL = "moonshotai/kimi-k2-instruct-0905"


def get_provider(
    provider_name: str = None,
    model: str = None,
    api_key: str = None
):
    """
    Returns an initialized provider instance.

    Priority:
    1. If provider_name is given → use that provider with the model
    2. If only model is given → look up which provider handles that model
    3. If neither → use default provider and model

    Examples:
        get_provider("gemini")
        get_provider(model="llama-3.3-70b-versatile")
        get_provider("ollama", model="codellama")
        get_provider()  # returns default
    """

    # Case 1 — model given, no provider → look up provider from model
    if model and not provider_name:
        provider_name = MODEL_TO_PROVIDER.get(model)
        if not provider_name:
            # Unknown model — check if Ollama is running and treat as local model
            provider_name = "ollama"

    # Case 2 — nothing given → use defaults
    if not provider_name:
        provider_name = DEFAULT_PROVIDER
        model = model or DEFAULT_MODEL

    # Validate provider name
    if provider_name not in PROVIDER_MAP:
        available = ", ".join(PROVIDER_MAP.keys())
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Available providers: {available}"
        )

    ProviderClass = PROVIDER_MAP[provider_name]

    kwargs = {}
    if model:
        kwargs["model"] = model
    if api_key:
        kwargs["api_key"] = api_key

    return ProviderClass(**kwargs)


def chat_with_retry(
        provider,
        messages: list[dict],
        tools: list[dict] = None,
        max_retries: int = 4,
        base_delay: float = 2.0
) -> dict:
    """
    Calls provider.chat() with exponential backoff retry logic.

    If the provider hits a rate limit or temporary error, it waits
    and retries automatically instead of crashing the session.

    Exponential backoff means:
        attempt 1 fails → wait 2s  → retry
        attempt 2 fails → wait 4s  → retry
        attempt 3 fails → wait 8s  → retry
        attempt 4 fails → wait 16s → retry
        attempt 5 fails → give up, raise error

    A small random jitter is added to each wait to avoid
    multiple retries hammering the API at the exact same time.

    Args:
        provider:     initialized provider instance
        messages:     conversation history
        tools:        tool definitions
        max_retries:  how many times to retry before giving up
        base_delay:   starting wait time in seconds
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return provider.chat(messages, tools)

        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()

            is_rate_limit = any(keyword in error_msg for keyword in [
                "rate limit", "rate_limit", "429",
                "too many requests", "quota",
                "capacity", "overloaded", "503", "502",
            ])

            if not is_rate_limit:
                raise e

            if attempt == max_retries:
                break

            wait_time = (base_delay ** (attempt + 1)) + random.uniform(0, 1)

            from rich.console import Console
            Console().print(
                f"\n[yellow]⚠ Rate limited. Retrying in {wait_time:.1f}s "
                f"(attempt {attempt + 1}/{max_retries})...[/yellow]"
            )
            time.sleep(wait_time)

    raise Exception(
        f"Provider failed after {max_retries} retries. "
        f"Last error: {last_exception}\n"
        f"Tip: switch providers with 'switch to gemini' or 'switch to openai'"
    )

def list_all_models() -> dict[str, list[str]]:
    """
    Returns all available models grouped by provider.
    Used when the user wants to browse models in a session.
    """
    return {
        name: PROVIDER_MAP[name]().get_available_models()
        if name == "ollama"
        else PROVIDER_MAP[name](model=DEFAULT_MODEL).get_available_models()
        for name in PROVIDER_MAP
        if name != "ollama"
    }
