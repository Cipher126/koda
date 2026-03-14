import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from dotenv import load_dotenv
load_dotenv()

app = typer.Typer(no_args_is_help=False)
console = Console()


def main():
    app(prog_name="koda")


@app.command("start")
def start(
    model: str = typer.Option(
        None, "--model", "-m",
        help="Model to use e.g. gemini-2.0-flash, llama-3.3-70b-versatile"
    ),
    provider: str = typer.Option(
        None, "--provider", "-p",
        help="Provider to use e.g. gemini, groq, openai, grok, ollama"
    ),
    tokens: bool = typer.Option(
        False, "--tokens", "-t",
        help="Show detailed token usage after every response."
    ),
    dir: str = typer.Option(
        None, "--dir", "-d",
        help="Project directory to work in. Defaults to current directory."
    ),
):
    """Start a Koda session."""
    from agent.controller import Controller
    from agent.formatter import print_error

    try:
        controller = Controller(
            provider_name=provider,
            model=model,
            project_dir=dir,
            tokens=tokens
        )
        controller.start()
    except Exception as e:
        print_error(f"Could not start Koda: {e}")
        raise typer.Exit(1)


@app.command("version")
def version():
    """Show Koda version."""
    console.print("[cyan]Koda v0.1.0[/cyan]")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    """
    Koda — AI Coding Assistant
    """
    if ctx.invoked_subcommand is not None:
        return

    _print_info()


def _print_info():
    """
    Print the full Koda information screen.
    Shown when `koda` is typed with no subcommand or flags.
    """

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Koda[/bold cyan] [dim]v0.1.0[/dim]\n"
        "[dim]An AI-powered coding assistant that lives in your terminal.[/dim]\n"
        "[dim]Build, debug, refactor, and understand code — conversationally.[/dim]",
        border_style="cyan"
    ))

    console.print("\n[bold cyan]What is Koda?[/bold cyan]")
    console.print(
        "  Koda is a session-based AI coding agent. Unlike one-shot tools,\n"
        "  Koda stays alive in your terminal for an entire work session.\n"
        "  You talk to it naturally, it builds and fixes real code on your machine,\n"
        "  and every change it makes can be rolled back instantly."
    )

    console.print("\n[bold cyan]Capabilities[/bold cyan]")

    cap_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    cap_table.add_column("Icon", style="cyan", no_wrap=True)
    cap_table.add_column("Capability", style="white")
    cap_table.add_column("Description", style="dim")

    cap_table.add_row("🏗", "Build projects",    "Scaffold entire apps from a single description")
    cap_table.add_row("🐛", "Debug code",        "Autonomously run, find errors, fix, and re-run")
    cap_table.add_row("🔧", "Refactor code",     "Improve structure, style, and performance")
    cap_table.add_row("📖", "Explain code",      "Plain language explanations of any code")
    cap_table.add_row("▶",  "Run code",          "Execute files and capture output in real time")
    cap_table.add_row("↩",  "Rollback changes",  "Undo any file change instantly")
    cap_table.add_row("➕", "Complete code",     "Add features or finish incomplete code")
    cap_table.add_row("💬", "Conversational",    "Persistent session — Koda remembers context")

    console.print(cap_table)

    console.print("\n[bold cyan]Supported Languages[/bold cyan]")

    lang_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    lang_table.add_column("Language", style="cyan")
    lang_table.add_column("Extensions", style="dim")

    lang_table.add_row("Python",     ".py")
    lang_table.add_row("JavaScript", ".js  .mjs  .cjs  .ts")
    lang_table.add_row("Java",       ".java")

    console.print(lang_table)

    console.print("\n[bold cyan]Supported AI Providers[/bold cyan]")

    prov_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    prov_table.add_column("Provider", style="cyan", no_wrap=True)
    prov_table.add_column("Models", style="white")
    prov_table.add_column("Key required", style="dim")

    prov_table.add_row(
        "groq (default)",
        "llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b",
        "GROQ_API_KEY"
    )
    prov_table.add_row(
        "gemini",
        "gemini-2.0-flash, gemini-1.5-pro",
        "GEMINI_API_KEY"
    )
    prov_table.add_row(
        "openai",
        "gpt-4o, gpt-4o-mini, gpt-4-turbo",
        "OPENAI_API_KEY"
    )
    prov_table.add_row(
        "grok",
        "grok-3, grok-3-mini, grok-3-fast",
        "XAI_API_KEY"
    )
    prov_table.add_row(
        "ollama",
        "llama3, codellama, mistral, phi3 (local)",
        "None — runs locally"
    )

    console.print(prov_table)

    console.print("\n[bold cyan]Setup[/bold cyan]")
    console.print(
        "  [dim]1.[/dim] Add your API keys to [cyan].env[/cyan] in the project root:\n"
        "\n"
        "       [dim]GROQ_API_KEY=your_key_here[/dim]\n"
        "       [dim]GEMINI_API_KEY=your_key_here[/dim]\n"
        "       [dim]OPENAI_API_KEY=your_key_here[/dim]\n"
        "       [dim]XAI_API_KEY=your_key_here[/dim]\n"
        "\n"
        "  [dim]2.[/dim] For Ollama (local models), install from [cyan]https://ollama.com[/cyan]\n"
        "       then pull a model:\n"
        "\n"
        "       [dim]ollama pull llama3[/dim]\n"
        "\n"
        "  [dim]3.[/dim] Start a session:\n"
        "\n"
        "       [dim]koda start[/dim]"
    )

    console.print("\n[bold cyan]Usage[/bold cyan]")

    usage_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    usage_table.add_column("Command", style="cyan", no_wrap=True)
    usage_table.add_column("Description", style="dim")

    usage_table.add_row("koda start",                      "Start a session with default provider (Groq)")
    usage_table.add_row("koda start --provider gemini",    "Start with a specific provider")
    usage_table.add_row("koda start --model gpt-4o-mini",  "Start with a specific model")
    usage_table.add_row("koda start --dir ./my-project",   "Start in a specific directory")
    usage_table.add_row("koda version",                    "Show version")
    usage_table.add_row("koda --help",                     "Show help")

    console.print(usage_table)

    console.print("\n[bold cyan]In-Session Commands[/bold cyan]")

    session_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    session_table.add_column("Command", style="cyan", no_wrap=True)
    session_table.add_column("Description", style="dim")

    session_table.add_row("switch to <provider>",  "Switch AI provider mid-session")
    session_table.add_row("use <model>",            "Switch model mid-session")
    session_table.add_row("cd <path>",              "Change working directory")
    session_table.add_row("clear history",          "Reset conversation context")
    session_table.add_row("snapshots",              "List available rollback points")
    session_table.add_row("models",                 "Show all available models")
    session_table.add_row("session",                "Show current session info")
    session_table.add_row("help",                   "Show in-session help")
    session_table.add_row("exit",                   "End session")

    console.print(session_table)

    console.print("\n[bold cyan]Example Session[/bold cyan]")
    console.print(
        "  [green]you →[/green] build me a todo app in python\n"
        "  [cyan]koda →[/cyan] ⚙ Planning project structure...\n"
        "          ⚙ Creating files...\n"
        "          ⚙ Running main.py...\n"
        "          Project 'todo-app' created! 5 files written.\n\n"
        "  [green]you →[/green] add a delete task feature\n"
        "  [cyan]koda →[/cyan] ⚙ Reading main.py...\n"
        "          ⚙ Appending to main.py...\n"
        "          Done! Added delete_task() function.\n\n"
        "  [green]you →[/green] i don't like that, roll it back\n"
        "  [cyan]koda →[/cyan] ⚙ Rolling back main.py...\n"
        "          Rolled back main.py to snap_003 ✓\n\n"
        "  [green]you →[/green] exit\n"
        "  [cyan]koda →[/cyan] Session ended. 3 actions, 2 files touched."
    )

    console.print()
    console.print(Panel.fit(
        "[dim]Run [/dim][cyan]koda start[/cyan][dim] to begin.[/dim]",
        border_style="cyan"
    ))
    console.print()


if __name__ == "__main__":
    main()