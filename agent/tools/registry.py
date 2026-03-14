from agent.snapshot import list_snapshots, rollback
from agent.tools.list_directory import list_directory
from agent.tools.read_file import read_file, get_session_info
from agent.tools.summarize_file import summarize_file
from agent.tools.write_file import write_file, append_to_file, replace_block
from agent.tools.create_project import create_project
from agent.tools.run_code import run_code
from agent.tools.debug import debug_code
from agent.tools.refactor import refactor_code
from agent.tools.detect_language import detect_language


TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file from disk. "
            "Use this before analyzing, debugging, explaining, or refactoring any file. "
            "Always read a file first before making any changes to it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the project directory."
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file on disk. Creates the file if it doesn't exist, "
            "overwrites it if it does. A snapshot is automatically taken before "
            "overwriting so the user can roll back if needed. "
            "Use this when creating new files or saving fixes and refactors."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write, relative to the project directory."
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write into the file."
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "create_project",
        "description": (
            "Scaffold an entire project structure from scratch. "
            "Use this when the user asks to build, create, or generate a new project or app. "
            "Creates all necessary files and folders based on the project type and language."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project and its root folder."
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "java"],
                    "description": "Programming language for the project."
                },
                "description": {
                    "type": "string",
                    "description": "What the project should do. Used to generate relevant files and code."
                },
                "project_dir": {
                    "type": "string",
                    "description": "Directory where the project folder should be created."
                }
            },
            "required": ["project_name", "language", "description"]
        }
    },
    {
        "name": "run_code",
        "description": (
            "Execute a code file and capture its output and any errors. "
            "Use this after creating or modifying code to verify it works. "
            "Also use when the user asks to run or test their code. "
            "Returns both stdout and stderr so errors can be analyzed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to execute."
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "java"],
                    "description": "Programming language of the file."
                }
            },
            "required": ["file_path", "language"]
        }
    },
    {
        "name": "debug_code",
        "description": (
            "Automatically debug a file by reading it, running it, analyzing errors, "
            "applying fixes, and re-running until the code works or max attempts are reached. "
            "Use this when the user reports a bug or when run_code returns errors. "
            "Do not use run_code and debug_code on the same file at the same time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to debug."
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "java"],
                    "description": "Programming language of the file."
                },
                "error_context": {
                    "type": "string",
                    "description": "Optional. Any error message or context the user provided about the bug."
                }
            },
            "required": ["file_path", "language"]
        }
    },
    {
        "name": "refactor_code",
        "description": (
            "Refactor or improve existing code in a file. "
            "Use when the user asks to improve, clean up, optimize, or restructure code. "
            "Always reads the file first, applies improvements, then writes it back. "
            "A snapshot is taken automatically before changes are saved."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to refactor."
                },
                "instructions": {
                    "type": "string",
                    "description": "Specific refactoring instructions e.g. 'improve error handling' or 'optimize the loop'."
                }
            },
            "required": ["file_path", "instructions"]
        }
    },
    {
        "name": "detect_language",
        "description": (
            "Detect the programming language of a file based on its extension. "
            "Use this when the user provides a file but doesn't specify the language, "
            "before running or debugging it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file whose language should be detected."
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "replace_block",
        "description": (
            "Replace a specific block of code in a file without touching the rest. "
            "Use this when fixing a bug or updating a specific function. "
            "Always read the file first to get the exact block to replace. "
            "Never use write_file for partial edits — use this instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit."
                },
                "old_content": {
                    "type": "string",
                    "description": "The exact block of code to find and replace. Must match the file exactly."
                },
                "new_content": {
                    "type": "string",
                    "description": "The new code to replace the old block with."
                }
            },
            "required": ["file_path", "old_content", "new_content"]
        }
    },
    {
        "name": "append_to_file",
        "description": (
            "Append new code to the end of an existing file. "
            "Use this when completing unfinished code or adding new functions/classes "
            "without modifying what already exists in the file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to append to."
                },
                "content": {
                    "type": "string",
                    "description": "The code to append at the end of the file."
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "rollback",
        "description": (
            "Roll back a file to its previous version before the last change. "
            "Use when the user says they don't like a change, want to undo, "
            "or want to revert a file. Can roll back the last change, "
            "a specific file, or a specific snapshot by ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Roll back the most recent snapshot of this specific file."
                },
                "snap_id": {
                    "type": "string",
                    "description": "Roll back a specific snapshot by ID e.g. snap_003."
                }
            },
            "required": []
        }
    },
    {
        "name": "list_snapshots",
        "description": (
            "List all available snapshots the user can roll back to. "
            "Use when the user asks what they can undo or wants to see snapshot history."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Optional. Filter snapshots to just this file."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_session_info",
        "description": (
            "Get current session information including the active project directory, "
            "provider, and model. Use this when the user asks about their current "
            "directory, project, or session settings."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_directory",
        "description": (
            "List all real files and directories at a given path on disk. "
            "Use this when the user asks what files exist in a folder, "
            "wants to explore a directory, or asks about project structure. "
            "Never guess or hallucinate directory contents — always use this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to list. Defaults to current project directory if not provided."
                }
            },
            "required": []
        }
    },
    {
        "name": "summarize_file",
        "description": (
            "Returns a one-paragraph summary of what a file does without reading "
            "its full contents. Use this when you need to understand a file's "
            "purpose without burning tokens on the full content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to summarize"
                }
            },
            "required": ["file_path"]
        }
    },
]


TOOL_EXECUTOR_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "create_project": create_project,
    "run_code": run_code,
    "debug_code": debug_code,
    "refactor_code": refactor_code,
    "detect_language": detect_language,
    "replace_block": replace_block,
    "append_to_file": append_to_file,
    "rollback": rollback,
    "list_snapshots": list_snapshots,
    "get_session_info": get_session_info,
    "list_directory": list_directory,
    "summarize_file": summarize_file,
}


def get_tool_schemas() -> list[dict]:
    """Return all tool schemas to pass to the LLM."""
    return TOOL_SCHEMAS


def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    Execute a tool by name with the given arguments.
    Called by the controller whenever the LLM requests a tool call.

    Returns the result as a string to send back to the LLM.
    """
    if tool_name not in TOOL_EXECUTOR_MAP:
        return f"Error: Unknown tool '{tool_name}'. Available tools: {list(TOOL_EXECUTOR_MAP.keys())}"

    tool_function = TOOL_EXECUTOR_MAP[tool_name]

    try:
        result = tool_function(**arguments)
        return str(result)
    except TypeError as e:
        return f"Error: Tool '{tool_name}' received wrong arguments. {e}"
    except Exception as e:
        return f"Error executing '{tool_name}': {e}"