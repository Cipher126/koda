import os
from rich.spinner import Spinner
from rich.live import Live
from agent.session import Session
from agent.ai_handler import AIHandler
from agent.formatter import (
    console,
    print_response,
    print_user_prompt,
    print_welcome,
    print_session_info,
    print_session_summary,
    print_help,
    print_dim,
    print_error,
    print_warning,
    get_spinner_text,
)


class Controller:
    """
    Orchestrates the Koda session.
    Connects CLI input → Session → AIHandler → formatted output.
    Intercepts local commands before they reach the LLM.
    """

    def __init__(
        self,
        provider_name: str = None,
        model: str = None,
        project_dir: str = None,
        tokens: bool = False,
    ):
        try:
            self.session = Session(
                provider_name=provider_name,
                model=model,
                project_dir=project_dir
            )
        except Exception as e:
            print_error(f"Failed to start session: {e}")
            raise

        self.session.token_tracker.verbose = tokens

        self.ai_handler = AIHandler(self.session)
        self.running = False

        self.ai_handler = AIHandler(self.session)

        self.running = False

    def start(self):
        """
        Start the session loop.
        Runs until the user types exit/quit/bye.
        """
        self.running = True

        print_welcome(
            provider_name=self.session.provider_name,
            model=self.session.model,
            project_dir=self.session.project_dir
        )

        while self.running:
            try:
                user_input = print_user_prompt()

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "bye"):
                    self._end_session()
                    break

                if self._handle_local_command(user_input):
                    continue

                self._process_message(user_input)

            except KeyboardInterrupt:
                console.print()
                self._end_session()
                break
            except Exception as e:
                import traceback
                console.print(f"\n[red]Unexpected error: {e}[/red]")
                console.print(traceback.format_exc())
                print_dim("You can keep going or type 'exit' to quit.")

    def _end_session(self):
        """Clean up and save session on exit."""
        self.running = False

        print_session_summary(self.session.get_summary())

        saved_path = self.session.save()
        if saved_path and not saved_path.startswith("Warning"):
            print_dim(f"Session saved → {saved_path}")
        elif saved_path:
            print_dim(saved_path)

        token_summary = self.session.token_tracker.format_session_summary()
        if token_summary:
            console.print(f"\n[dim]Token Summary:[/dim]\n{token_summary}")

        print_dim("Goodbye! 👋")


    def _process_message(self, user_input: str):
        """
        Send a message to the AI handler and display the response.
        Shows a spinner while waiting for the LLM.
        """
        with Live(
            Spinner("dots", text=get_spinner_text()),
            console=console,
            transient=True
        ):
            response, usage = self.ai_handler.process(user_input)

        print_response(response)

        if usage:
            token_display = self.session.token_tracker.format_request(usage)
            if token_display:
                console.print(token_display)


    def _handle_local_command(self, user_input: str) -> bool:
        """
        Check if the input is a local command that doesn't need the LLM.
        Returns True if handled locally, False if should go to LLM.
        """
        lower = user_input.lower().strip()

        if lower in ("clear history", "clear chat", "reset history"):
            result = self.session.clear_history()
            print_response(result)
            return True

        if user_input.startswith("--provider ") or user_input.startswith("--model "):
            return self._handle_inline_flags(user_input)

        if lower.startswith("switch to ") or lower.startswith("use "):
            return self._handle_switch_command(user_input)

        if lower in ("session", "session info", "status"):
            print_session_info(
                session_id=self.session.session_id,
                provider_name=self.session.provider_name,
                model=self.session.model,
                project_dir=self.session.project_dir,
                message_count=len(self.session.messages)
            )
            return True

        if lower in ("snapshots", "list snapshots", "show snapshots"):
            from agent.snapshot import list_snapshots
            result = list_snapshots()
            print_response(result)
            return True

        if lower.startswith("cd "):
            return self._handle_cd_command(user_input)

        if lower in ("models", "list models", "show models"):
            return self._handle_models_command()

        if lower in ("help", "commands", "?"):
            print_help()
            return True

        return False

    def _handle_switch_command(self, user_input: str) -> bool:
        """
        Handle provider/model switching commands.
        e.g. "switch to gemini", "use groq", "switch to gpt-4o"
        """
        from agent.providers import PROVIDER_MAP, MODEL_TO_PROVIDER

        lower = user_input.lower().strip()

        target = (
            lower.replace("switch to ", "")
                 .replace("use ", "")
                 .strip()
        )

        if target in PROVIDER_MAP:
            result = self.session.switch_provider(provider_name=target)
            print_response(result)
            return True

        if target in MODEL_TO_PROVIDER:
            result = self.session.switch_provider(model=target)
            print_response(result)
            return True

        print_warning(f"'{target}' not recognized as a provider or model. Asking Koda...")
        return False

    def _handle_inline_flags(self, user_input: str) -> bool:
        """
        Handle --provider and --model flags typed mid-session.
        e.g. "--provider gemini", "--model mixtral-8x7b-32768"
        """
        parts = user_input.strip().split()
        provider_name = None
        model = None

        i = 0
        while i < len(parts):
            if parts[i] == "--provider" and i + 1 < len(parts):
                provider_name = parts[i + 1]
                i += 2
            elif parts[i] == "--model" and i + 1 < len(parts):
                model = parts[i + 1]
                i += 2
            else:
                i += 1

        if not provider_name and not model:
            return False

        result = self.session.switch_provider(
            provider_name=provider_name,
            model=model
        )
        print_response(result)
        return True

    def _handle_cd_command(self, user_input: str) -> bool:
        """
        Handle directory change commands.
        e.g. "cd ./my-project", "cd C:/Users/admin/projects"
        """
        path = user_input[3:].strip()

        if not os.path.isabs(path):
            path = os.path.join(self.session.project_dir, path)

        path = os.path.normpath(path)

        try:
            self.session.set_project_dir(path)
            print_response(f"Working directory set to [cyan]{path}[/cyan] ✓")
        except ValueError as e:
            print_error(str(e))

        return True

    def _handle_models_command(self) -> bool:
        """
        Show all available models grouped by provider.
        """
        from agent.formatter import print_models_table
        from agent.providers import PROVIDER_MAP, DEFAULT_MODEL

        models_by_provider = {}
        for name, ProviderClass in PROVIDER_MAP.items():
            try:
                if name == "ollama":
                    instance = ProviderClass()
                    models_by_provider[name] = instance.get_available_models()
                else:
                    instance = ProviderClass(model=DEFAULT_MODEL)
                    models_by_provider[name] = instance.get_available_models()
            except Exception:
                models_by_provider[name] = ["(unavailable — check API key)"]

        print_models_table(models_by_provider)
        return True