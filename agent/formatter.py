from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box


console = Console()


STYLE_PRIMARY     = "bold cyan"       # Koda's name, main actions
STYLE_SUCCESS     = "bold green"      # Success messages
STYLE_ERROR       = "bold red"        # Error messages
STYLE_WARNING     = "yellow"          # Warnings
STYLE_DIM         = "dim"             # Subtle info, hints
STYLE_USER        = "bold green"      # User prompt arrow
STYLE_TOOL        = "dim cyan"        # Tool call notifications
STYLE_BORDER      = "cyan"            # Panel borders
STYLE_CODE        = "monokai"         # Syntax highlight theme


def print_response(response: str):
    """
    Display Koda's response in the terminal.
    Renders markdown if detected, plain text otherwise.
    """
    console.print(f"\n[{STYLE_PRIMARY}]koda →[/{STYLE_PRIMARY}]")

    if _contains_markdown(response):
        console.print(Markdown(response))
    else:
        console.print(response)


def print_user_prompt() -> str:
    """
    Print the user input prompt and return the input.
    Centralizes the prompt style.
    """
    return console.input(f"\n[{STYLE_USER}]you →[/{STYLE_USER}] ").strip()


def print_tool_call(tool_name: str, description: str):
    """
    Print a subtle notification when a tool is being called.
    """
    console.print(f"  [{STYLE_TOOL}]⚙ {description}...[/{STYLE_TOOL}]")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[{STYLE_SUCCESS}]✓ {message}[/{STYLE_SUCCESS}]")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[{STYLE_ERROR}]✗ {message}[/{STYLE_ERROR}]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[{STYLE_WARNING}]⚠ {message}[/{STYLE_WARNING}]")


def print_dim(message: str):
    """Print subtle/secondary information."""
    console.print(f"[{STYLE_DIM}]{message}[/{STYLE_DIM}]")


def print_welcome(provider_name: str, model: str, project_dir: str):
    """Print the Koda welcome panel at session start."""
    console.print(Panel.fit(
        f"[{STYLE_PRIMARY}]Welcome to Koda[/{STYLE_PRIMARY}] 🤖\n"
        f"[{STYLE_DIM}]Your AI coding assistant. "
        f"Type your request or 'exit' to quit.[/{STYLE_DIM}]\n\n"
        f"[{STYLE_DIM}]provider : {provider_name}[/{STYLE_DIM}]\n"
        f"[{STYLE_DIM}]model    : {model}[/{STYLE_DIM}]\n"
        f"[{STYLE_DIM}]dir      : {project_dir}[/{STYLE_DIM}]",
        border_style=STYLE_BORDER
    ))


def print_session_info(
    session_id: str,
    provider_name: str,
    model: str,
    project_dir: str,
    message_count: int
):
    """Print detailed session info panel."""
    console.print(Panel.fit(
        f"[bold]Session ID:[/bold]  {session_id}\n"
        f"[bold]Provider:[/bold]    {provider_name}\n"
        f"[bold]Model:[/bold]       {model}\n"
        f"[bold]Project dir:[/bold] {project_dir}\n"
        f"[bold]Messages:[/bold]    {message_count}",
        title=f"[{STYLE_PRIMARY}]Koda Session[/{STYLE_PRIMARY}]",
        border_style=STYLE_BORDER
    ))


def print_session_summary(summary: str):
    """Print the session summary at exit."""
    console.print(f"\n[{STYLE_PRIMARY}]{summary}[/{STYLE_PRIMARY}]")


def print_help():
    """Print the help panel."""
    console.print(Panel(
        f"[bold]Local Commands[/bold] (no AI needed)\n\n"
        f"  [{STYLE_PRIMARY}]switch to <provider>[/{STYLE_PRIMARY}]   "
        f"Switch provider e.g. 'switch to gemini'\n"
        f"  [{STYLE_PRIMARY}]use <model>[/{STYLE_PRIMARY}]            "
        f"Switch model e.g. 'use gpt-4o-mini'\n"
        f"  [{STYLE_PRIMARY}]cd <path>[/{STYLE_PRIMARY}]              "
        f"Change working directory\n"
        f"  [{STYLE_PRIMARY}]clear history[/{STYLE_PRIMARY}]          "
        f"Reset conversation history\n"
        f"  [{STYLE_PRIMARY}]snapshots[/{STYLE_PRIMARY}]              "
        f"List available rollback points\n"
        f"  [{STYLE_PRIMARY}]session[/{STYLE_PRIMARY}]                "
        f"Show current session info\n"
        f"  [{STYLE_PRIMARY}]help[/{STYLE_PRIMARY}]                   "
        f"Show this message\n"
        f"  [{STYLE_PRIMARY}]exit[/{STYLE_PRIMARY}]                   "
        f"End session\n\n"
        f"[bold]Everything else[/bold] → sent to Koda AI",
        title=f"[{STYLE_PRIMARY}]Koda Help[/{STYLE_PRIMARY}]",
        border_style=STYLE_BORDER
    ))


def print_code(code: str, language: str = "python"):
    """
    Print a code block with syntax highlighting.
    Used when displaying generated or explained code.
    """
    syntax = Syntax(
        code,
        language,
        theme=STYLE_CODE,
        line_numbers=True,
        word_wrap=True
    )
    console.print(syntax)


def format_file_tree(files: list[str], project_name: str) -> str:
    """
    Format a list of file paths as a tree structure.
    Used in project creation summary.

    e.g.
    todo-app/
    ├── main.py
    ├── models/
    │   └── task.py
    └── storage.py
    """
    if not files:
        return f"{project_name}/ (empty)"

    lines = [f"{project_name}/"]
    sorted_files = sorted(files)

    for i, file_path in enumerate(sorted_files):
        is_last = i == len(sorted_files) - 1
        connector = "└──" if is_last else "├──"
        lines.append(f"  {connector} {file_path}")

    return "\n".join(lines)


def print_models_table(models_by_provider: dict[str, list[str]]):
    """
    Print available models grouped by provider as a table.
    Used when user asks 'what models are available?'
    """
    table = Table(
        title="Available Models",
        box=box.ROUNDED,
        border_style=STYLE_BORDER,
        header_style=STYLE_PRIMARY
    )

    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Models", style="white")

    for provider, models in models_by_provider.items():
        table.add_row(
            provider,
            "\n".join(models)
        )

    console.print(table)


def get_spinner_text() -> str:
    """Return the spinner label shown while Koda is thinking."""
    return f"[{STYLE_DIM}] Koda is thinking...[/{STYLE_DIM}]"


def _contains_markdown(text: str) -> bool:
    """
    Detect if a response contains markdown formatting.
    """
    indicators = ["```", "###", "## ", "# ", "**", "- ", "1. "]
    return any(indicator in text for indicator in indicators)