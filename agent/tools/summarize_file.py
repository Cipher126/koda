def summarize_file(file_path: str, project_dir: str = None) -> str:
    """
    Returns a one-paragraph summary of what a file does
    without returning its full contents.
    """
    import os
    from agent.providers import get_provider, PROVIDER_DEFAULTS, DEFAULT_PROVIDER

    if project_dir and not os.path.isabs(file_path):
        file_path = os.path.join(project_dir, file_path)

    file_path = os.path.normpath(file_path)

    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    if not content.strip():
        return f"'{file_path}' is empty."

    MAX_CHARS = 6000
    truncated = content[:MAX_CHARS]
    was_truncated = len(content) > MAX_CHARS

    try:
        provider = get_provider(DEFAULT_PROVIDER)
        response = provider.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize what this file does in one short paragraph. "
                        f"Focus on its purpose, main functions, and role in the project. "
                        f"Do not list every function — just explain what it does overall.\n\n"
                        f"File: {os.path.basename(file_path)}\n\n{truncated}"
                        + ("\n\n[File truncated]" if was_truncated else "")
                    )
                }
            ],
            tools=None
        )
        summary = response.get("content", "").strip()
        return f"Summary of '{file_path}':\n{summary}"

    except Exception as e:
        return f"Error summarizing file: {e}"