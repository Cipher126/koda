import json
from agent.providers import chat_with_retry
from agent.tools.registry import get_tool_schemas, execute_tool


SYSTEM_AS_USER_PROVIDERS = {"gemini"}

MAX_TOOL_ROUNDS = 8


class AIHandler:
    """
    Handles all communication between Koda and the LLM provider.
    Responsible for:
    - Formatting messages correctly per provider
    - Calling the LLM with retry logic
    - Executing tool calls the LLM requests
    - Feeding tool results back to the LLM
    - Injecting provider into tools that need it
    """

    def __init__(self, session):
        self.session = session
        self._last_request_usage = None

    def get_system_prompt(self) -> str:
        try:
            from agent.prompt import SYSTEM_PROMPT
            return SYSTEM_PROMPT
        except ImportError:
            return (
                "You are Koda, an AI coding assistant. "
                "Help the user build, debug, and improve code. "
                "Use the available tools to interact with files and run code."
            )

    def process(self, user_input: str):
        self.session.add_user_message(user_input)
        return self._run_agent_loop(), self._last_request_usage

    def _run_agent_loop(self) -> str:
        """
        The core agent loop.

        Sends messages to LLM → checks for tool calls →
        executes tools → feeds results back → repeats
        until LLM gives a final text response.
        """
        tool_round = 0

        while tool_round < MAX_TOOL_ROUNDS:
            messages = self._build_messages()

            try:
                response = chat_with_retry(
                    provider=self.session.provider,
                    messages=messages,
                    tools=get_tool_schemas()
                )
            except Exception as e:
                error_msg = str(e)

                # Detect rate limit / quota errors and return clean message
                if any(k in error_msg.lower() for k in [
                    "rate limit", "rate_limit", "429",
                    "quota", "resource_exhausted",
                    "too many requests", "capacity",
                    "overloaded", "503", "502"
                ]):
                    provider = self.session.provider_name
                    model = self.session.model
                    return (
                        f"Rate limited on {provider} ({model}). "
                        f"Try: 'switch to gemini', 'use llama-3.1-8b-instant', or 'switch to groq'"
                    )

                return f"Provider error: {str(e).splitlines()[0]}"

            if response is None:
                return "Error: Provider returned empty response. Try again."

            usage = response.get("usage")
            if usage:
                self._last_request_usage = self.session.token_tracker.record(
                    usage=usage,
                    provider=self.session.provider_name,
                    model=self.session.model
                )
            else:
                self._last_request_usage = None
                from agent.formatter import console

            content    = response.get("content")
            tool_calls = response.get("tool_calls", [])

            # No tool calls — LLM gave a final text response
            if not tool_calls:
                if content:
                    self.session.add_assistant_message(content)
                    return content
                return "Error: LLM returned empty response."

            tool_round += 1

            # Groq and OpenAI require the assistant message to include
            # the full tool_calls array before tool results are sent back
            assistant_message = {
                "role":       "assistant",
                "content":    content or "",
                "tool_calls": [
                    {
                        "id":       tc.get("id"),
                        "type":     "function",
                        "function": {
                            "name":      tc.get("name"),
                            "arguments": json.dumps(tc.get("arguments", {}))
                        }
                    }
                    for tc in tool_calls
                ]
            }
            self.session.messages.append(assistant_message)

            # Execute each tool call and feed results back
            for tool_call in tool_calls:
                tool_name    = tool_call.get("name")
                arguments    = tool_call.get("arguments") or {}
                tool_call_id = tool_call.get("id")

                self._notify_tool_call(tool_name, arguments)

                arguments = self._inject_provider(tool_name, arguments)
                arguments = self._inject_project_dir(tool_name, arguments)

                result = execute_tool(tool_name, arguments)

                self._track_files(tool_name, arguments)
                self._track_action(tool_name, arguments, result)

                self.session.add_tool_result(tool_name, result, tool_call_id)

        return (
            "Error: Agent exceeded maximum tool call rounds. "
            "Try rephrasing your request or breaking it into smaller steps."
        )

    def _build_messages(self) -> list[dict]:
        system_prompt = self.get_system_prompt()
        provider_name = self.session.provider_name

        if provider_name in SYSTEM_AS_USER_PROVIDERS:
            return self._build_gemini_messages(system_prompt)

        return self.session.get_messages_with_system(system_prompt)

    def _build_gemini_messages(self, system_prompt: str) -> list[dict]:
        messages = []

        messages.append({
            "role": "user",
            "content": f"[System Instructions]\n{system_prompt}"
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I am Koda, ready to help."
        })

        for msg in self.session.messages:
            if msg["role"] == "tool":
                messages.append({
                    "role": "user",
                    "content": f"[Tool result from {msg.get('name', 'tool')}]:\n{msg['content']}"
                })
            elif msg["role"] == "assistant" and "tool_calls" in msg:
                if msg.get("content"):
                    messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
            else:
                messages.append(msg)

        return messages
    def _inject_provider(self, tool_name: str, arguments: dict) -> dict:
        PROVIDER_TOOLS = {"debug_code", "refactor_code", "create_project"}
        if tool_name in PROVIDER_TOOLS:
            arguments = {**arguments, "provider": self.session.provider}
        return arguments

    def _inject_project_dir(self, tool_name: str, arguments: dict) -> dict:
        FILE_TOOLS = {
            "read_file", "write_file", "replace_block",
            "append_to_file", "run_code", "debug_code",
            "refactor_code", "detect_language",
            "list_directory", "get_session_info", "summarize_file"
        }
        if tool_name in FILE_TOOLS and "project_dir" not in arguments:
            arguments = {**arguments, "project_dir": self.session.project_dir}
        return arguments

    def _notify_tool_call(self, tool_name: str, arguments: dict):
        from agent.formatter import print_tool_call
        descriptions = {
            "read_file":        f"Reading {arguments.get('file_path', '')}",
            "write_file":       f"Writing {arguments.get('file_path', '')}",
            "replace_block":    f"Updating {arguments.get('file_path', '')}",
            "append_to_file":   f"Appending to {arguments.get('file_path', '')}",
            "create_project":   f"Creating project '{arguments.get('project_name', '')}'",
            "run_code":         f"Running {arguments.get('file_path', '')}",
            "debug_code":       f"Debugging {arguments.get('file_path', '')}",
            "refactor_code":    f"Refactoring {arguments.get('file_path', '')}",
            "detect_language":  f"Detecting language of {arguments.get('file_path', '')}",
            "rollback":         f"Rolling back {arguments.get('file_path', 'last change')}",
            "list_snapshots":   "Listing snapshots",
            "get_session_info": "Getting session info",
            "list_directory":   f"Listing {arguments.get('path', 'current directory')}",
            "summarize_file": f"Summarizing {arguments.get('file_path', '')}",
        }
        description = descriptions.get(tool_name, tool_name)
        print_tool_call(tool_name, description)

    def _track_files(self, tool_name: str, arguments: dict):
        WRITE_TOOLS = {"write_file", "replace_block", "append_to_file"}
        if tool_name in WRITE_TOOLS:
            file_path = arguments.get("file_path")
            if file_path:
                self.session.track_file(file_path)
        elif tool_name == "create_project":
            project_name = arguments.get("project_name", "")
            self.session.track_file(f"{project_name}/ (project)")

    def _track_action(self, tool_name: str, arguments: dict, result: str):
        action_map = {
            "create_project": f"Created project '{arguments.get('project_name', '')}'",
            "debug_code":     f"Debugged '{arguments.get('file_path', '')}'",
            "refactor_code":  f"Refactored '{arguments.get('file_path', '')}'",
            "rollback":       f"Rolled back '{arguments.get('file_path', 'last change')}'",
            "write_file":     f"Wrote '{arguments.get('file_path', '')}'",
            "replace_block":  f"Updated '{arguments.get('file_path', '')}'",
            "append_to_file": f"Appended to '{arguments.get('file_path', '')}'",
        }
        action = action_map.get(tool_name)
        if action:
            self.session.track_action(action)