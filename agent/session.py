import os
import uuid
import json
from datetime import datetime
from agent.providers import get_provider, DEFAULT_PROVIDER, DEFAULT_MODEL
from agent.tokens import TokenTracker


SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")


class Session:
    """
    Manages the state of a single Koda session.
    Tracks conversation history, active provider,
    project context, and files touched.
    Saves a summary to disk when the session ends.
    """

    def __init__(
        self,
        provider_name: str = None,
        model: str = None,
        project_dir: str = None,
    ):
        from agent.providers import DEFAULT_PROVIDER, PROVIDER_DEFAULTS

        self.provider_name = provider_name or DEFAULT_PROVIDER
        if model:
            self.model = model
        else:
            self.model = PROVIDER_DEFAULTS.get(self.provider_name, DEFAULT_MODEL)

        self.session_id = str(uuid.uuid4())[:8]

        self.started_at = datetime.now()

        self.messages = []

        self.files_touched = set()

        self.actions = []

        self.project_dir = project_dir or os.getcwd()

        self.provider_name = provider_name or DEFAULT_PROVIDER
        self.model = model or DEFAULT_MODEL
        self.provider = self._init_provider(self.provider_name, self.model)
        self.token_tracker = TokenTracker(verbose=False)

    def _init_provider(self, provider_name: str, model: str):
        """
        Initialize the LLM provider.
        Returns the provider instance or raises with a helpful message.
        """
        try:
            return get_provider(provider_name=provider_name, model=model)
        except ValueError as e:
            raise ValueError(f"Could not initialize provider '{provider_name}': {e}")
        except Exception as e:
            raise Exception(f"Failed to load provider '{provider_name}': {e}")


    def add_user_message(self, content: str):
        """Add a user message to conversation history."""
        self.messages.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(self, content: str):
        """Add an assistant message to conversation history."""
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def add_tool_result(self, tool_name: str, result: str, tool_call_id: str = None):
        """
        Add a tool result to conversation history.
        tool_call_id is required by Groq and OpenAI.
        """
        message = {
            "role": "tool",
            "name": tool_name,
            "content": result,
        }
        if tool_call_id:
            message["tool_call_id"] = tool_call_id

        self.messages.append(message)

    def get_messages_with_system(self, system_prompt: str) -> list[dict]:
        """
        Return full conversation history with system prompt prepended.
        This is what gets sent to the LLM on every call.
        """
        return [
            {"role": "system", "content": system_prompt},
            *self.messages
        ]


    def track_file(self, file_path: str):
        """Record that a file was touched this session."""
        self.files_touched.add(file_path)

    def track_action(self, action: str):
        """Record an action taken this session e.g. 'Created project todo-app'."""
        self.actions.append({
            "action": action,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def set_project_dir(self, project_dir: str):
        """
        Update the active project directory.
        Called when user starts working on a different project.
        """
        if not os.path.exists(project_dir):
            raise ValueError(f"Directory '{project_dir}' does not exist.")
        self.project_dir = project_dir

    def switch_provider(self, provider_name: str = None, model: str = None) -> str:
        """
        Switch to a different provider or model mid session.
        Conversation history is preserved — the new provider
        gets full context of what happened before the switch.

        Returns confirmation message.
        """
        from agent.providers import PROVIDER_DEFAULTS

        new_provider_name = provider_name or self.provider_name

        if model:
            new_model = model
        elif provider_name and provider_name != self.provider_name:
            new_model = PROVIDER_DEFAULTS.get(provider_name, self.model)
        else:
            new_model = self.model

        try:
            new_provider = self._init_provider(new_provider_name, new_model)
            self.provider = new_provider
            self.provider_name = new_provider_name
            self.model = new_model
            return (
                f"Switched to {new_provider_name} "
                f"({new_model}) ✓"
            )
        except Exception as e:
            return f"Error switching provider: {e}"

    def save(self) -> str:
        """
        Save a summary of this session to disk as a JSON file.
        Called automatically when the session ends.
        Stores only the summary — not the full message history.
        """
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        duration = datetime.now() - self.started_at
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)

        summary_data = {
            "session_id":    self.session_id,
            "started_at":    self.started_at.isoformat(),
            "ended_at":      datetime.now().isoformat(),
            "duration":      f"{minutes}m {seconds}s",
            "provider":      self.provider_name,
            "model":         self.model,
            "project_dir":   self.project_dir,
            "message_count": len(self.messages),
            "files_touched": sorted(list(self.files_touched)),
            "actions": [
                {
                    "timestamp": entry["timestamp"],
                    "action":    entry["action"]
                }
                for entry in self.actions
            ]
        }

        filename = (
            f"session_{self.session_id}_"
            f"{self.started_at.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )
        filepath = os.path.join(SESSIONS_DIR, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)
            return filepath
        except Exception as e:
            return f"Warning: Could not save session: {e}"


    def get_summary(self) -> str:
        """
        Generate a human readable summary of what happened this session.
        Shown when the user exits.
        """
        duration = datetime.now() - self.started_at
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)

        parts = [
            "─" * 40,
            "Session Summary",
            "─" * 40,
            f"  Session ID:  {self.session_id}",
            f"  Duration:    {minutes}m {seconds}s",
            f"  Provider:    {self.provider_name} ({self.model})",
            f"  Project dir: {self.project_dir}",
            f"  Messages:    {len(self.messages)}",
            "",
        ]

        if self.actions:
            parts.append("Actions taken:")
            for entry in self.actions:
                parts.append(f"  [{entry['timestamp']}] {entry['action']}")
            parts.append("")

        if self.files_touched:
            parts.append("Files touched:")
            for f in sorted(self.files_touched):
                parts.append(f"  {f}")
            parts.append("")

        parts.append("─" * 40)

        return "\n".join(parts)


    def clear_history(self) -> str:
        """
        Clear conversation history but keep session state.
        Useful if context window gets too large mid session.
        """
        count = len(self.messages)
        self.messages = []
        return f"Cleared {count} messages from conversation history."

    def __repr__(self):
        return (
            f"Session(id={self.session_id}, "
            f"provider={self.provider_name}, "
            f"model={self.model}, "
            f"messages={len(self.messages)})"
        )