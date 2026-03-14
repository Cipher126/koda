import os
from agent.tools.run_code import run_code
from agent.tools.read_file import read_file_raw
from agent.tools.write_file import write_file


MAX_ATTEMPTS = 5


def debug_code(
    file_path: str,
    language: str,
    error_context: str = None,
    project_dir: str = None,
    provider=None,
) -> str:
    """
    Autonomously debug a file by running it, analyzing errors,
    applying fixes, and re-running until it works or attempts run out.

    Args:
        file_path:     Path to the file to debug
        language:      Programming language of the file
        error_context: Optional error message the user already knows about
        project_dir:   Working directory context
        provider:      LLM provider instance for generating fixes
                       (injected by the controller)

    Returns:
        Summary of what was debugged and fixed
    """
    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return f"Error: File '{full_path}' does not exist."

    if not provider:
        return (
            "Error: No LLM provider available for debugging. "
            "Cannot analyze errors without an AI provider."
        )

    attempt = 0
    history = []

    while attempt < MAX_ATTEMPTS:
        attempt += 1

        current_code = read_file_raw(full_path)
        if not current_code:
            return f"Error: Could not read '{file_path}'."

        run_result = run_code(file_path, language, project_dir)

        if "✓ Success" in run_result:
            summary = _build_summary(
                file_path=file_path,
                attempts=attempt,
                history=history,
                success=True,
                final_output=run_result
            )
            return summary

        fix_prompt = _build_fix_prompt(
            file_path=file_path,
            language=language,
            code=current_code,
            run_result=run_result,
            error_context=error_context if attempt == 1 else None,
            attempt=attempt,
            max_attempts=MAX_ATTEMPTS
        )

        try:
            from agent.providers import chat_with_retry
            response = chat_with_retry(
                provider=provider,
                messages=[{"role": "user", "content": fix_prompt}]
            )
            fix_content = response.get("content", "")
        except Exception as e:
            return f"Error getting fix from LLM: {e}"

        if not fix_content:
            return "Error: LLM returned empty fix. Cannot continue debugging."

        fixed_code = _extract_code(fix_content)

        if not fixed_code:
            history.append({
                "attempt": attempt,
                "error": run_result,
                "fix": "Could not extract code from LLM response"
            })
            continue

        write_result = write_file(file_path, fixed_code, project_dir)

        history.append({
            "attempt": attempt,
            "error": _extract_error(run_result),
            "fix": write_result
        })

    final_run = run_code(file_path, language, project_dir)

    return _build_summary(
        file_path=file_path,
        attempts=attempt,
        history=history,
        success="✓ Success" in final_run,
        final_output=final_run
    )


def _build_fix_prompt(
    file_path: str,
    language: str,
    code: str,
    run_result: str,
    error_context: str,
    attempt: int,
    max_attempts: int
) -> str:
    """
    Build a focused prompt asking the LLM to fix a specific error.
    """
    prompt_parts = [
        f"You are debugging a {language} file: {file_path}",
        f"This is attempt {attempt} of {max_attempts}.",
        "",
        "Current code:",
        "```",
        code,
        "```",
        "",
        "Execution result:",
        run_result,
    ]

    if error_context:
        prompt_parts += ["", f"Additional context from user: {error_context}"]

    prompt_parts += [
        "",
        "Return ONLY the complete fixed code with no explanation, "
        "no markdown, no backticks. Just the raw code.",
    ]

    return "\n".join(prompt_parts)


def _extract_code(response: str) -> str:
    """
    Extract clean code from LLM response.
    Handles cases where LLM wraps code in markdown backticks
    despite being told not to.
    """

    if "```" in response:
        lines = response.split("\n")
        code_lines = []
        inside_block = False

        for line in lines:
            if line.strip().startswith("```"):
                inside_block = not inside_block
                continue
            if inside_block:
                code_lines.append(line)

        return "\n".join(code_lines).strip()

    return response.strip()


def _extract_error(run_result: str) -> str:
    """
    Extract just the error message from a run_code result.
    Used for the debug summary.
    """
    if "Errors:" in run_result:
        return run_result.split("Errors:")[-1].strip()
    return run_result.strip()


def _build_summary(
    file_path: str,
    attempts: int,
    history: list[dict],
    success: bool,
    final_output: str
) -> str:
    """
    Build a human readable summary of the debug session.
    """
    status = "✓ Fixed" if success else "✗ Could not fix"
    lines = [
        f"Debug summary for '{file_path}':",
        f"Status: {status} after {attempts} attempt(s)",
        "",
    ]

    for entry in history:
        lines.append(f"Attempt {entry['attempt']}:")
        lines.append(f"  Error:  {entry['error'][:100]}...")
        lines.append(f"  Action: {entry['fix']}")
        lines.append("")

    lines.append("Final run result:")
    lines.append(final_output)

    return "\n".join(lines)


def _resolve_path(file_path: str, project_dir: str = None) -> str:
    """Resolve relative paths against project_dir."""
    if project_dir and not os.path.isabs(file_path):
        return os.path.join(project_dir, file_path)
    return file_path