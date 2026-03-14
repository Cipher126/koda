import os
import json
from agent.tools.write_file import write_multiple_files
from agent.tools.run_code import run_code


def create_project(
    project_name: str,
    language: str,
    description: str,
    project_dir: str = None,
    provider=None,
) -> str:
    """
    Scaffold an entire project from scratch based on a description.
    Plans the structure, generates all files, writes them to disk,
    and runs the entry point to verify everything works.

    Args:
        project_name: Name of the project and root folder
        language:     Programming language (python, javascript, java)
        description:  What the project should do
        project_dir:  Where to create the project folder
                      Defaults to current working directory
        provider:     LLM provider instance (injected by controller)

    Returns:
        Summary of project created and initial run result
    """
    if not provider:
        return "Error: No LLM provider available for project creation."

    base_dir = project_dir or os.getcwd()
    full_project_path = os.path.join(base_dir, project_name)

    if os.path.exists(full_project_path):
        return (
            f"Error: Directory '{full_project_path}' already exists. "
            f"Choose a different project name or delete the existing folder."
        )

    plan = _plan_project(
        project_name=project_name,
        language=language,
        description=description,
        provider=provider
    )

    if isinstance(plan, str) and plan.startswith("Error"):
        return plan

    result = _generate_files(
        project_name=project_name,
        language=language,
        description=description,
        plan=plan,
        provider=provider
    )

    if isinstance(result, str) and result.startswith("Error"):
        return result

    explanation = result.get("explanation", "")
    actual_files = result.get("files", {})

    if not actual_files:
        return "Error: No files were generated for the project."

    os.makedirs(full_project_path, exist_ok=True)
    write_result = write_multiple_files(actual_files, project_dir=full_project_path)

    entry_point = plan.get("entry_point")
    run_result = ""

    if entry_point:
        run_result = run_code(
            file_path=entry_point,
            language=language,
            project_dir=full_project_path
        )

    return _build_summary(
        project_name=project_name,
        language=language,
        description=description,
        full_project_path=full_project_path,
        plan=plan,
        write_result=write_result,
        run_result=run_result,
        explanation=explanation
    )


def _plan_project(
    project_name: str,
    language: str,
    description: str,
    provider
):
    """
    Ask the LLM to plan the project structure.
    Returns a dict describing the files needed.
    """
    prompt = "\n".join([
        f"Plan a {language} project called '{project_name}'.",
        f"Description: {description}",
        "",
        "Return ONLY a JSON object with this exact structure:",
        "{",
        '  "files": ["main.py", "utils/helper.py", ...],',
        '  "entry_point": "main.py",',
        '  "description": "brief description of the project structure"',
        "}",
        "",
        "Rules:",
        f"- Use only {language} files",
        "- Keep it simple and functional",
        "- entry_point must be one of the files listed",
        "- Return ONLY the JSON, no explanation, no markdown, no backticks",
    ])

    try:
        from agent.providers import chat_with_retry
        response = chat_with_retry(
            provider=provider,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.get("content", "")
    except Exception as e:
        return f"Error planning project: {e}"

    try:
        clean = _strip_json(content)
        plan = json.loads(clean)

        if "files" not in plan or "entry_point" not in plan:
            return "Error: LLM returned invalid project plan. Missing required fields."

        return plan

    except json.JSONDecodeError:
        return f"Error: Could not parse project plan from LLM response: {content[:200]}"


def _generate_files(
    project_name: str,
    language: str,
    description: str,
    plan: dict,
    provider
):
    """
    Ask the LLM to generate content for each file in the plan.
    Returns a dict with 'files' mapping file_path → content
    and 'explanation' describing the project.
    """
    files_list = "\n".join(f"- {f}" for f in plan["files"])

    prompt = "\n".join([
        f"Generate complete code for a {language} project called '{project_name}'.",
        f"Description: {description}",
        "",
        "Project structure:",
        files_list,
        f"Entry point: {plan['entry_point']}",
        "",
        "Return ONLY a JSON object with this exact structure:",
        "{",
        '  "files": {',
        '    "main.py": "# complete code here",',
        '    "utils/helper.py": "# complete code here"',
        '  },',
        '  "explanation": "A clear explanation of how the project works, what each file does, and how to use it"',
        "}",
        "",
        "Rules:",
        "- Write complete, working, runnable code for every file",
        "- No placeholder comments like '# add code here'",
        "- Write clean, well structured, production quality code",
        f"- Use only {language}",
        "- Return ONLY the JSON, no explanation, no markdown, no backticks",
    ])

    try:
        from agent.providers import chat_with_retry
        response = chat_with_retry(
            provider=provider,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.get("content", "")
    except Exception as e:
        return f"Error generating files: {e}"

    # Parse the JSON response
    try:
        clean = _strip_json(content)
        parsed = json.loads(clean)

        if not isinstance(parsed, dict):
            return "Error: LLM returned invalid file structure."

        # Extract explanation and actual files separately
        explanation = parsed.get("explanation", "")
        actual_files = parsed.get("files", parsed)  # fallback to root if LLM ignored structure

        return {"files": actual_files, "explanation": explanation}

    except json.JSONDecodeError:
        return f"Error: Could not parse generated files from LLM response: {content[:200]}"


def _strip_json(content: str) -> str:
    """
    Strip markdown and extract raw JSON from LLM response.
    Handles cases where LLM wraps JSON in backticks despite instructions.
    """
    content = content.strip()

    if "```" in content:
        lines = content.split("\n")
        json_lines = []
        inside_block = False

        for line in lines:
            if line.strip().startswith("```"):
                inside_block = not inside_block
                continue
            if inside_block:
                json_lines.append(line)

        content = "\n".join(json_lines).strip()

    start = content.find("{")
    end = content.rfind("}") + 1

    if start != -1 and end > start:
        return content[start:end]

    return content


def _build_summary(
    project_name: str,
    language: str,
    description: str,
    full_project_path: str,
    plan: dict,
    write_result: str,
    run_result: str,
    explanation: str = ""
) -> str:
    """
    Build a human readable summary of the created project.
    """
    files_list = "\n".join(f"    {f}" for f in plan.get("files", []))

    parts = [
        f"Project '{project_name}' created!",
        f"  Language:    {language}",
        f"  Description: {description}",
        f"  Location:    {full_project_path}",
        f"  Entry point: {plan.get('entry_point')}",
        "",
    ]

    if explanation:
        parts += [
            "About this project:",
            f"  {explanation}",
            "",
        ]

    parts += [
        "Files created:",
        files_list,
        "",
        write_result,
    ]

    if run_result:
        parts += ["", "Initial run:", run_result]

    parts += [
        "",
        "You can now:",
        "  - Ask me to explain any file",
        "  - Ask me to add new features",
        "  - Ask me to debug if there are errors",
        "  - Say 'roll back' to undo any changes",
    ]

    return "\n".join(parts)