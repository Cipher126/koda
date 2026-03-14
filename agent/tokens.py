from dataclasses import dataclass, field
from datetime import datetime


DAILY_LIMITS = {
    "groq": {
        "llama-3.3-70b-versatile": 100_000,
        "llama-3.1-8b-instant":    500_000,
        "llama3-8b-8192":          500_000,
        "llama3-70b-8192":         100_000,
        "mixtral-8x7b-32768":      100_000,
        "gemma2-9b-it":            500_000,
    },
    "gemini": {
        "gemini-2.0-flash":      1_000_000,
        "gemini-2.0-flash-lite": 1_000_000,
        "gemini-2.5-flash":      1_000_000,
        "gemini-1.5-pro":          50_000,
    },
    "openai":  {},   # Paid — no hard daily limit
    "grok":    {},   # Paid — no hard daily limit
    "ollama":  {},   # Local — unlimited
}


@dataclass
class RequestUsage:
    """Token usage for a single LLM request."""
    prompt_tokens:     int = 0
    completion_tokens: int = 0
    total_tokens:      int = 0
    provider:          str = ""
    model:             str = ""
    timestamp:         str = field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S")
    )


@dataclass
class SessionUsage:
    """Cumulative token usage across the entire session."""
    total_prompt_tokens:     int = 0
    total_completion_tokens: int = 0
    total_tokens:            int = 0
    request_count:           int = 0
    requests:                list = field(default_factory=list)


class TokenTracker:
    """
    Tracks token usage across a session.
    Receives usage data from providers after each LLM call,
    accumulates session totals, and formats display output.
    """

    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: If True, show detailed token info after each response.
                     If False, show only a dim summary line.
        """
        self.verbose = verbose
        self.session = SessionUsage()

    def record(self, usage: dict, provider: str, model: str) -> RequestUsage:
        """
        Record token usage from a provider response.
        Called by ai_handler after every LLM call.

        Args:
            usage:    Raw usage dict from provider response
                      e.g. {"prompt_tokens": 120, "completion_tokens": 80}
            provider: Provider name e.g. "groq"
            model:    Model name e.g. "llama-3.1-8b-instant"

        Returns:
            RequestUsage object with this request's data
        """
        if not usage:
            return RequestUsage(provider=provider, model=model)

        request = RequestUsage(
            prompt_tokens     = usage.get("prompt_tokens", 0),
            completion_tokens = usage.get("completion_tokens", 0),
            total_tokens      = usage.get("total_tokens", 0),
            provider          = provider,
            model             = model,
        )


        self.session.total_prompt_tokens     += request.prompt_tokens
        self.session.total_completion_tokens += request.completion_tokens
        self.session.total_tokens            += request.total_tokens
        self.session.request_count           += 1
        self.session.requests.append(request)

        return request

    def format_request(self, request: RequestUsage) -> str:
        """
        Format token usage for a single request.
        Dim mode: one short line
        Verbose mode: full breakdown
        """
        if request.total_tokens == 0:
            return ""

        daily_limit = self._get_daily_limit(request.provider, request.model)
        remaining   = self._get_remaining(request.provider, request.model)

        if self.verbose:
            lines = [
                f"\n  [dim]── Token Usage ──────────────────[/dim]",
                f"  [dim]  This request : {request.prompt_tokens:,} prompt + "
                f"{request.completion_tokens:,} completion = "
                f"[bold]{request.total_tokens:,} total[/bold][/dim]",
                f"  [dim]  Session total: {self.session.total_tokens:,} tokens "
                f"across {self.session.request_count} requests[/dim]",
            ]

            if daily_limit:
                used_pct = (self.session.total_tokens / daily_limit) * 100
                lines.append(
                    f"  [dim]  Daily limit  : {self.session.total_tokens:,} / "
                    f"{daily_limit:,} used ({used_pct:.1f}%)[/dim]"
                )
                if remaining is not None:
                    lines.append(
                        f"  [dim]  Remaining    : ~{remaining:,} tokens[/dim]"
                    )


                if used_pct >= 90:
                    lines.append(
                        f"  [yellow]  ⚠ Warning: {used_pct:.0f}% of daily limit used. "
                        f"Consider switching providers.[/yellow]"
                    )
                elif used_pct >= 75:
                    lines.append(
                        f"  [dim yellow]  ⚠ {used_pct:.0f}% of daily limit used.[/dim yellow]"
                    )

            lines.append(f"  [dim]────────────────────────────────[/dim]")
            return "\n".join(lines)

        else:
            # Dim single line
            parts = [
                f"[dim]  ↳ {request.total_tokens:,} tokens "
                f"(session: {self.session.total_tokens:,})"
            ]

            if daily_limit and remaining is not None:
                used_pct = (self.session.total_tokens / daily_limit) * 100
                parts.append(f"· ~{remaining:,} remaining today")

                # Still warn even in dim mode if critical
                if used_pct >= 90:
                    parts.append(f"· [yellow]⚠ {used_pct:.0f}% of daily limit[/yellow]")

            parts.append("[/dim]")
            return " ".join(parts)

    def format_session_summary(self) -> str:
        """
        Format full session token summary.
        Called at session end.
        """
        if self.session.total_tokens == 0:
            return ""

        lines = [
            f"  Token usage  : {self.session.total_tokens:,} total tokens",
            f"  Breakdown    : {self.session.total_prompt_tokens:,} prompt + "
            f"{self.session.total_completion_tokens:,} completion",
            f"  LLM calls    : {self.session.request_count}",
        ]

        if self.session.request_count > 0:
            avg = self.session.total_tokens // self.session.request_count
            lines.append(f"  Avg per call : {avg:,} tokens")

        return "\n".join(lines)


    def _get_daily_limit(self, provider: str, model: str) -> int | None:
        """Get the known daily token limit for a provider/model."""
        provider_limits = DAILY_LIMITS.get(provider, {})
        return provider_limits.get(model)

    def _get_remaining(self, provider: str, model: str) -> int | None:
        """
        Estimate remaining tokens for today.
        Based on session usage — not perfectly accurate since
        tokens used in other sessions aren't tracked here.
        """
        daily_limit = self._get_daily_limit(provider, model)
        if not daily_limit:
            return None
        remaining = daily_limit - self.session.total_tokens
        return max(0, remaining)