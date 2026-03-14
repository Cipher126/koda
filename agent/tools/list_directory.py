def list_directory(path: str = None, project_dir: str = None) -> str:
    """List all files and directories at a given path."""
    import os

    IGNORED_DIRS = {
        ".git", ".venv", "__pycache__", "node_modules",
        ".idea", "dist", "build", ".next", ".cache",
        "venv", "env", ".mypy_cache", "target", "out",
        ".pytest_cache", ".tox", "coverage", ".coverage",
    }

    IGNORED_EXTENSIONS = {
        ".iml", ".class", ".pyc", ".pyo",
    }

    IGNORED_FILES = {
        ".DS_Store", "Thumbs.db", ".gitkeep",
    }

    if path:
        path = path.strip().rstrip("/").rstrip("\\")

        if path in (".", "./", "/", ""):
            path = project_dir or os.getcwd()
        elif not os.path.isabs(path):
            base = project_dir or os.getcwd()
            path = os.path.join(base, path)
    else:
        path = project_dir or os.getcwd()

    path = os.path.normpath(path)

    if not os.path.exists(path):
        return (
            f"Error: Path '{path}' does not exist. "
            f"Current project directory is: {project_dir or os.getcwd()}"
        )

    if not os.path.isdir(path):
        return f"Error: '{path}' is a file, not a directory."

    try:
        entries = os.listdir(path)
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'."

    if not entries:
        return f"Directory '{path}' is empty."

    dirs = sorted([
        e for e in entries
        if os.path.isdir(os.path.join(path, e)) and e not in IGNORED_DIRS
    ])
    files = sorted([
        e for e in entries
        if os.path.isfile(os.path.join(path, e))
        and e not in IGNORED_FILES
        and os.path.splitext(e)[1] not in IGNORED_EXTENSIONS
    ])

    if not dirs and not files:
        return f"Directory '{path}' contains only ignored system folders."

    lines = [f"Contents of '{path}':", ""]

    for d in dirs:
        lines.append(f"  📁 {d}/")
    for f in files:
        lines.append(f"  📄 {f}")

    lines.append(f"\n{len(dirs)} directories, {len(files)} files")

    return "\n".join(lines)