import os
from agent.tools.read_file import read_file_raw
from agent.tools.write_file import write_file


def refactor_code(
    file_path: str,
    instructions: str,
    project_dir: str = None,
    provider=None,
) -> str:
    """
    Refactor or improve existing code based on instructions.
    Reads the file, asks the LLM to improve it, snapshots
    the original, then writes the improved version back.

    Args:
        file_path:    Path to the file to refactor
        instructions: What to improve e.g. "add error handling",
                      "optimize the loop", "add type hints"
        project_dir:  Working directory context
        provider:     LLM provider instance (injected by controller)

    Returns:
        Summary of changes made
    """
    full_path = _resolve_path(file_path, project_dir)

    if not os.path.exists(full_path):
        return f"Error: File '{full_path}' does not exist."

    if not provider:
        return (
            "Error: No LLM provider available for refactoring. "
        )

    original_code = read_file_raw(full_path)
    if not original_code:
        return f"Error: Could not read '{file_path}'."

    original_line_count = len(original_code.splitlines())

    prompt = _build_refactor_prompt(
        file_path=file_path,
        code=original_code,
        instructions=instructions
    )

    try:
        from agent.providers import chat_with_retry
        response = chat_with_retry(
            provider=provider,
            messages=[{"role": "user", "content": prompt}]
        )
        refactored_content = response.get("content", "")
    except Exception as e:
        return f"Error getting refactored code from LLM: {e}"

    if not refactored_content:
        return "Error: LLM returned empty response. Refactor aborted."

    refactored_code = _extract_code(refactored_content)

    if not refactored_code:
        return "Error: Could not extract code from LLM response. Refactor aborted."

    refactored_line_count = len(refactored_code.splitlines())
    if refactored_line_count < original_line_count * 0.5:
        return (
            f"Error: Refactored code ({refactored_line_count} lines) is suspiciously "
            f"shorter than original ({original_line_count} lines). "
            f"Refactor aborted to protect your file. Try more specific instructions."
        )

    write_result = write_file(file_path, refactored_code, project_dir)

    if write_result.startswith("Error"):
        return write_result

    # Step 5 — Build summary
    return _build_summary(
        file_path=file_path,
        instructions=instructions,
        original_lines=original_line_count,
        refactored_lines=refactored_line_count,
        write_result=write_result
    )


def _build_refactor_prompt(
    file_path: str,
    code: str,
    instructions: str
) -> str:
    """
    Build a focused prompt for the LLM to refactor code.
    """
    return "\n".join([
        f"You are refactoring the following code from file: {file_path}",
        "",
        "Refactoring instructions:",
        instructions,
        "",
        "Original code:",
        "```",
        code,
        "```",
        "",
        "Rules:",
        "- Keep the same overall behavior and logic",
        "- Do not remove existing functionality",
        "- Apply ONLY the requested improvements",
        "- Return the complete refactored file",
        "- Return ONLY raw code, no explanation, no markdown, no backticks",
    ])


def _extract_code(response: str) -> str:
    """
    Extract clean code from LLM response.
    Strips markdown backticks if the LLM included them.
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

        extracted = "\n".join(code_lines).strip()
        return extracted if extracted else response.strip()

    return response.strip()


def _build_summary(
    file_path: str,
    instructions: str,
    original_lines: int,
    refactored_lines: int,
    write_result: str
) -> str:
    """
    Build a human readable summary of the refactor.
    """
    line_diff = refactored_lines - original_lines
    diff_str = (
        f"+{line_diff} lines" if line_diff > 0
        else f"{line_diff} lines" if line_diff < 0
        else "same number of lines"
    )

    return "\n".join([
        f"Refactor complete for '{file_path}':",
        f"  Instructions: {instructions}",
        f"  Original:     {original_lines} lines",
        f"  Refactored:   {refactored_lines} lines ({diff_str})",
        f"  {write_result}",
        "",
        "You can roll back with: 'roll back the changes to this file'"
    ])


def _resolve_path(file_path: str, project_dir: str = None) -> str:
    """Resolve relative paths against project_dir."""
    if project_dir and not os.path.isabs(file_path):
        return os.path.join(project_dir, file_path)
    return file_path