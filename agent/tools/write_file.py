import os


def write_file(file_path: str, content: str, project_dir: str = None) -> str:
    """
    Write content to a file on disk.
    Automatically snapshots the file before overwriting
    so the user can roll back if needed.

    Args:
        file_path:   Path to the file to write
        content:     Full content to write into the file
        project_dir: Optional base directory for relative paths

    Returns:
        Success or error message string
    """
    # Resolve full path
    full_path = _resolve_path(file_path, project_dir)

    # Snapshot existing file before overwriting
    snapshot_info = ""
    if os.path.exists(full_path):
        try:
            from agent.snapshot import take_snapshot
            snapshot_id = take_snapshot(full_path)
            snapshot_info = f" (snapshot saved: {snapshot_id})"
        except Exception as e:
            # Snapshot failure shouldn't block the write
            # Just warn and continue
            snapshot_info = f" (warning: snapshot failed: {e})"

    # Create parent directories if they don't exist
    # e.g. if writing to src/utils/helper.py and src/utils/ doesn't exist
    parent_dir = os.path.dirname(full_path)
    if parent_dir:
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as e:
            return f"Error: Could not create directory '{parent_dir}': {e}"

    # Write the file
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    except PermissionError:
        return f"Error: Permission denied writing to '{full_path}'."
    except Exception as e:
        return f"Error writing to '{full_path}': {e}"

    # Count lines written for feedback
    line_count = len(content.splitlines())

    return (
        f"Successfully wrote {line_count} lines to '{full_path}'"
        f"{snapshot_info}"
    )


def write_multiple_files(files: dict[str, str], project_dir: str = None) -> str:
    """
    Write multiple files at once.
    Used by create_project to scaffold an entire project in one shot.

    Args:
        files: dict mapping file_path → content
               e.g. {"main.py": "print('hello')", "utils/helper.py": "..."}
        project_dir: base directory for all files

    Returns:
        Summary of all files written and any errors
    """
    results = []
    success_count = 0
    error_count = 0

    for file_path, content in files.items():
        result = write_file(file_path, content, project_dir)

        if result.startswith("Error"):
            error_count += 1
            results.append(f"  ✗ {file_path}: {result}")
        else:
            success_count += 1
            results.append(f"  ✓ {file_path}")

    summary = (
        f"Wrote {success_count} files successfully"
        + (f", {error_count} errors" if error_count else "")
        + ":\n"
        + "\n".join(results)
    )

    return summary


def replace_block(
    file_path: str,
    old_content: str,
    new_content: str,
    project_dir: str = None
) -> str:
    """
    Replace a specific block of code in a file without touching the rest.
    Use this when fixing a bug or updating a specific function/section.
    Always read the file first to get the exact block to replace.

    Args:
        file_path:   Path to the file
        old_content: The exact block of code to find and replace
        new_content: The new code to put in its place
        project_dir: Optional base directory

    Returns:
        Success or error message
    """
    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return f"Error: File '{full_path}' does not exist."

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return f"Error reading '{full_path}': {e}"

    if old_content not in original:
        return (
            f"Error: Could not find the specified block in '{file_path}'. "
            f"Read the file first and copy the exact block to replace."
        )

    # Check it's not ambiguous — block should appear exactly once
    occurrences = original.count(old_content)
    if occurrences > 1:
        return (
            f"Error: The block appears {occurrences} times in '{file_path}'. "
            f"Provide a more specific block to avoid ambiguity."
        )

    # Snapshot before modifying
    snapshot_info = ""
    try:
        from agent.snapshot import take_snapshot
        snapshot_id = take_snapshot(full_path)
        snapshot_info = f" (snapshot saved: {snapshot_id})"
    except Exception as e:
        snapshot_info = f" (warning: snapshot failed: {e})"

    updated = original.replace(old_content, new_content, 1)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(updated)
    except Exception as e:
        return f"Error writing to '{full_path}': {e}"

    return f"Successfully updated block in '{file_path}'{snapshot_info}"


def append_to_file(
    file_path: str,
    content: str,
    project_dir: str = None
) -> str:
    """
    Append content to the end of an existing file.
    Use this when adding new functions, classes, or completing
    unfinished code without touching what's already there.

    Args:
        file_path:   Path to the file
        content:     Code to append
        project_dir: Optional base directory

    Returns:
        Success or error message
    """
    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return f"Error: File '{full_path}' does not exist. Use write_file to create it first."

    # Snapshot before modifying
    snapshot_info = ""
    try:
        from agent.snapshot import take_snapshot
        snapshot_id = take_snapshot(full_path)
        snapshot_info = f" (snapshot saved: {snapshot_id})"
    except Exception as e:
        snapshot_info = f" (warning: snapshot failed: {e})"

    try:
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(f"\n{content}")
    except PermissionError:
        return f"Error: Permission denied writing to '{full_path}'."
    except Exception as e:
        return f"Error appending to '{full_path}': {e}"

    line_count = len(content.splitlines())
    return f"Successfully appended {line_count} lines to '{file_path}'{snapshot_info}"


def _resolve_path(file_path: str, project_dir: str = None) -> str:
    """Resolve relative paths against project_dir."""
    if project_dir and not os.path.isabs(file_path):
        return os.path.join(project_dir, file_path)
    return file_path