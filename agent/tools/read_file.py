import os


MAX_LINES = 5000


def read_file(file_path: str, project_dir: str = None) -> str:
    """
    Read a file from disk and return its contents with metadata.

    Args:
        file_path:   Path to the file, relative to project_dir or absolute
        project_dir: Optional base directory to resolve relative paths from

    Returns:
        String containing file metadata + contents,
        or an error message if the file can't be read
    """

    full_path = _resolve_path(file_path, project_dir)


    if not os.path.exists(full_path):
        return (
            f"Error: File '{full_path}' does not exist. "
            f"Use create_project or write_file to create it first."
        )

    if not os.path.isfile(full_path):
        return f"Error: '{full_path}' is a directory, not a file."

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    except UnicodeDecodeError:
        return (
            f"Error: '{full_path}' appears to be a binary file "
            f"and cannot be read as text."
        )
    except PermissionError:
        return f"Error: Permission denied reading '{full_path}'."
    except Exception as e:
        return f"Error reading '{full_path}': {e}"

    total_lines = len(lines)
    truncated = False

    if total_lines > MAX_LINES:
        lines = lines[:MAX_LINES]
        truncated = True

    content = "".join(lines)

    # Build a rich response with metadata the LLM can use
    response_parts = [
        f"File: {full_path}",
        f"Lines: {total_lines}" + (" (truncated to 500)" if truncated else ""),
        f"Size: {os.path.getsize(full_path)} bytes",
        "---",
        content,
    ]

    if truncated:
        response_parts.append(
            f"\n[Note: File truncated at {MAX_LINES} lines. "
            f"{total_lines - MAX_LINES} lines not shown.]"
        )

    return "\n".join(response_parts)


def read_file_raw(file_path: str, project_dir: str = None) -> str:
    """
    Read a file and return ONLY its raw content, no metadata.
    Used internally by other tools like refactor and debug
    that need clean content without metadata noise.
    """
    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _resolve_path(file_path: str, project_dir: str = None) -> str:
    """
    Resolve a file path.
    If project_dir is given and file_path is relative,
    join them to get the full path.
    """
    if project_dir and not os.path.isabs(file_path):
        return os.path.join(project_dir, file_path)
    return file_path


def get_session_info(**kwargs) -> str:
    project_dir = kwargs.get("project_dir", "unknown")
    return (
        f"Current project directory: {project_dir}\n"
        f"This is the real path on disk where Koda is working."
    )