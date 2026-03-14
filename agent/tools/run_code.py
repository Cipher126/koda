import os
import subprocess
from agent.tools.detect_language import detect_language

TIMEOUT_SECONDS = 15


def run_code(file_path: str, language: str = None, project_dir: str = None) -> str:
    """
    Execute a code file and return its output and errors.

    Args:
        file_path:   Path to the file to run
        language:    Programming language. Auto-detected if not provided.
        project_dir: Working directory to run the code from.
                     Defaults to the file's parent directory.

    Returns:
        String containing exit status, stdout, and stderr
    """

    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return f"Error: File '{full_path}' does not exist."

    if not language:
        language = detect_language(full_path)
        if language.startswith("Error"):
            return language

    language = language.lower()

    working_dir = project_dir or os.path.dirname(full_path) or os.getcwd()

    if language == "python":
        return _run_python(full_path, working_dir)
    elif language == "javascript":
        return _run_javascript(full_path, working_dir)
    elif language == "java":
        return _run_java(full_path, working_dir)
    else:
        return f"Error: Unsupported language '{language}'."


def _run_python(file_path: str, working_dir: str) -> str:
    """Run a Python file."""
    return _execute(
        command=["python", file_path],
        working_dir=working_dir,
        label="Python"
    )


def _run_javascript(file_path: str, working_dir: str) -> str:
    """Run a JavaScript file with Node.js."""
    return _execute(
        command=["node", file_path],
        working_dir=working_dir,
        label="JavaScript"
    )


def _run_java(file_path: str, working_dir: str) -> str:
    """
    Run a Java file.
    Java requires two steps: compile with javac, then run with java.
    """
    compile_result = _execute(
        command=["javac", file_path],
        working_dir=working_dir,
        label="Java (compile)"
    )

    if "exit code: 0" not in compile_result:
        return f"Compilation failed:\n{compile_result}"

    class_name = os.path.splitext(os.path.basename(file_path))[0]

    return _execute(
        command=["java", "-cp", working_dir, class_name],
        working_dir=working_dir,
        label="Java (run)"
    )


def _execute(command: list[str], working_dir: str, label: str) -> str:
    """
    Execute a shell command and capture its output.

    Args:
        command:     Command as a list e.g. ["python", "main.py"]
        working_dir: Directory to run the command from
        label:       Human readable label for the output header

    Returns:
        Formatted string with exit code, stdout, and stderr
    """
    try:
        result = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )

        return _format_result(
            label=label,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )

    except subprocess.TimeoutExpired:
        return (
            f"[{label}] Execution timed out after {TIMEOUT_SECONDS} seconds.\n"
            f"The code may contain an infinite loop or blocking operation."
        )
    except FileNotFoundError:
        runtime = command[0]  # e.g. "python", "node", "java"
        return (
            f"Error: '{runtime}' is not installed or not in PATH.\n"
            f"Please install {runtime} to run {label} files."
        )
    except Exception as e:
        return f"Error executing code: {e}"


def _format_result(
    label: str,
    exit_code: int,
    stdout: str,
    stderr: str
) -> str:
    """
    Format execution results into a clean string the LLM can analyze.
    """
    status = "✓ Success" if exit_code == 0 else "✗ Failed"

    parts = [
        f"[{label}] {status} (exit code: {exit_code})",
    ]

    if stdout.strip():
        parts.append(f"\nOutput:\n{stdout.strip()}")
    else:
        parts.append("\nOutput: (none)")

    if stderr.strip():
        parts.append(f"\nErrors:\n{stderr.strip()}")

    return "\n".join(parts)


def _resolve_path(file_path: str, project_dir: str = None) -> str:
    """Resolve relative paths against project_dir."""
    if project_dir and not os.path.isabs(file_path):
        return os.path.join(project_dir, file_path)
    return file_path
