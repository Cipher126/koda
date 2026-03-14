# Koda — AI Coding Assistant

Koda is a session-based, AI-powered command-line interface (CLI) coding assistant designed to help developers build, understand, debug, and improve code directly from the terminal. Unlike one-shot tools, Koda maintains context throughout your work session, allowing for natural, conversational interactions. Every change made by Koda can be instantly rolled back.

## Features

*   **Build Projects**: Scaffold entire applications from a single description in Python, JavaScript, or Java.
*   **Debug Code**: Autonomously run, identify errors, apply fixes, and re-run code until it works.
*   **Refactor Code**: Improve code structure, style, and performance with specific instructions.
*   **Explain Code**: Get plain language explanations for any piece of code.
*   **Run Code**: Execute files and capture real-time output, including errors.
*   **Rollback Changes**: Undo any file modification instantly.
*   **Complete Code**: Add new features or finish incomplete code.
*   **Conversational**: Persistent session with remembered context for seamless interaction.

## Supported Languages

Koda currently supports the following programming languages:

*   **Python**: `.py`
*   **JavaScript**: `.js`, `.mjs`, `.cjs`, `.ts`
*   **Java**: `.java`

## Supported AI Providers

Koda can integrate with several AI providers, each offering various models:

| Provider         | Models                                          | API Key Environment Variable |
| :--------------- | :---------------------------------------------- | :--------------------------- |
| `groq` (default) | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b` | `GROQ_API_KEY`               |
| `gemini`         | `gemini-2.0-flash`, `gemini-1.5-pro`            | `GEMINI_API_KEY`             |
| `openai`         | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`          | `OPENAI_API_KEY`             |
| `grok`           | `grok-3`, `grok-3-mini`, `grok-3-fast`          | `XAI_API_KEY`                |
| `ollama`         | `llama3`, `codellama`, `mistral`, `phi3` (local)| None — runs locally          |

## Project Structure

The project is structured to modularize different aspects of the Koda agent:

```
.
├── agent/
│   ├── providers/          # AI provider integrations (Gemini, Groq, OpenAI, Ollama)
│   ├── tools/              # Core functionalities exposed to the AI (read, write, debug, create, etc.)
│   ├── __init__.py
│   ├── ai_handler.py       # Handles AI model interaction and tool calling
│   ├── cli.py              # Command-line interface definitions and entry points
│   ├── controller.py       # Orchestrates sessions, manages user input and AI responses
│   ├── formatter.py        # Utility for rich console output formatting
│   ├── prompt.py           # Manages prompts for AI interaction
│   ├── session.py          # Handles session state, history, and project context
│   ├── snapshot.py         # Manages file snapshots for rollback functionality
│   └── tokens.py           # Token usage tracking
├── sessions/               # Stores saved session data
├── snapshots/              # Stores file snapshots for rollback
├── tests/                  # Project tests
├── .env                    # Environment variables for API keys
├── .gitignore              # Git ignore file
├── .python-version         # Python version specification
├── README.md               # This README file
├── main.py                 # Main entry point for the application, calls agent.cli.main
├── pyproject.toml          # Project metadata, dependencies, and build configuration
└── uv.lock                 # Dependency lock file
```

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/FabiyiPelumi/Koda.git
    cd Koda
    ```
2.  **Install dependencies**:
    ```bash
    uv tool install --editable .
    ```

## Setup

1.  **API Keys**: Create a `.env` file in the project root and add your API keys. **Do not commit your actual API keys to version control.** Examples:
    ```
    GROQ_API_KEY=your_groq_api_key
    GEMINI_API_KEY=your_gemini_api_key
    OPENAI_API_KEY=your_openai_api_key
    XAI_API_KEY=your_xai_api_key
    ```
2.  **Ollama (for local models)**:
    *   Install Ollama from [https://ollama.com](https://ollama.com).
    *   Pull a model, for example: `ollama pull llama3`
3.  **Start a session**:
    ```bash
    koda start
    ```

## Usage

### CLI Commands

*   `koda start`: Start a Koda session with the default provider (Groq).
*   `koda start --provider gemini`: Start a session with a specific AI provider.
*   `koda start --model gpt-4o-mini`: Start a session with a specific AI model.
*   `koda start --dir ./my-project`: Start a session within a specified project directory.
*   `koda start --tokens`: Show detailed token usage after every response.
*   `koda version`: Display Koda's version.
*   `koda --help`: Show help information for Koda CLI commands.

### In-Session Commands

Once a Koda session is active, you can use these commands:

*   `switch to <provider>`: Change the AI provider during a session (e.g., `switch to gemini`).
*   `use <model>`: Change the AI model during a session (e.g., `use gpt-4o`).
*   `cd <path>`: Change the current working directory within the session.
*   `clear history`: Reset the conversation context.
*   `snapshots`: List available rollback points.
*   `models`: Show all available models grouped by provider.
*   `session`: Display current session information (ID, provider, model, project directory).
*   `help`: Show in-session help.
*   `exit`: End the Koda session.

## Example Session

```bash
you → build me a todo app in python
koda → ⚙ Planning project structure...
        ⚙ Creating files...
        ⚙ Running main.py...
        Project 'todo-app' created! 5 files written.

you → add a delete task feature
koda → ⚙ Reading main.py...
        ⚙ Appending to main.py...
        Done! Added delete_task() function.

you → i don't like that, roll it back
koda → ⚙ Rolling back main.py...
        Rolled back main.py to snap_003 ✓

you → exit
koda → Session ended. 3 actions, 2 files touched.
Goodbye! 👋
```

Start building with Koda today! Run `koda start` to begin.
