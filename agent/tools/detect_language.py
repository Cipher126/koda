import os


EXTENSION_MAP = {
    # Python
    ".py":   "python",

    # JavaScript / TypeScript
    ".js":   "javascript",
    ".mjs":  "javascript",
    ".cjs":  "javascript",
    ".ts":   "javascript",

    # Java
    ".java": "java",
}

# Maps language → how to run it in the terminal
# Used by run_code and debug_code
LANGUAGE_RUN_COMMANDS = {
    "python":     "python",
    "javascript": "node",
    "java":       "java",
}


def detect_language(file_path: str) -> str:
    """
    Detect the programming language of a file from its extension.

    Args:
        file_path: Path to the file

    Returns:
        Language name as a string e.g. "python", "javascript", "java"
        or an error message if the extension is unsupported
    """
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    if not extension:
        return (
            f"Error: '{file_path}' has no file extension. "
            f"Cannot determine language."
        )

    language = EXTENSION_MAP.get(extension)

    if not language:
        supported = ", ".join(EXTENSION_MAP.keys())
        return (
            f"Error: Unsupported file extension '{extension}'. "
            f"Koda supports: {supported}"
        )

    return language


def get_run_command(language: str) -> str:
    """
    Get the terminal command used to run a given language.
    Used internally by run_code and debug_code.
    """
    return LANGUAGE_RUN_COMMANDS.get(language)