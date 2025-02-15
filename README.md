# AgentReadmeGen

An intelligent repository documentation generator powered by LangChain and GPT-4, designed to automatically analyze codebases and generate comprehensive README files. This tool serves as a benchmark comparison against AIDER for automated repository documentation generation.

## Overview

AgentReadmeGen is a Python-based tool that leverages (LLM) to analyze repository contents and automatically generate meaningful README.md. The project uses an agent-based approach to understand codebases across multiple programming languages, including Java, Python, and Node.js ecosystems.

## Key Features

- Multi-language support (Java, Python, Node.js ecosystems)
- Intelligent code analysis using GPT-4
- Automatic entry point detection
- Comprehensive repository structure analysis
- Smart documentation generation
- Language-specific feature detection (e.g., Spring Boot annotations, Maven/Gradle configurations)

## Project Structure

```
.
├── Pipfile             # Python dependencies and virtual environment configuration
├── Pipfile.lock        # Locked versions of dependencies
├── file_info.py        # File information schema definition
├── main.py            # Entry point and CLI interface
├── repo_analyzer_agent.py   # Core analysis agent implementation
├── repo_analyzer_tools.py   # Analysis tools and utilities
├── repo_info.py       # Repository information schema definition
└── .env               # Environment configuration
```

## Prerequisites

- Python 3.10
- OpenAI API key
- pipenv (for dependency management)

## Installation

1. Clone the repository
2. Install dependencies using pipenv:
```bash
pipenv install
```
3. Configure your OpenAI API key in `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the analyzer on a target repository:

```bash
python main.py
```

By default, the tool will:
1. Analyze the repository structure
2. Detect programming languages
3. Identify entry points
4. Generate a comprehensive README.md file

## Dependencies

- langchain - For LLM workflow management
- langchain-openai - OpenAI integration
- python-dotenv - Environment management
- langchainhub - Additional LangChain components
- black - Code formatting

## How It Works

1. **Repository Analysis**: The tool walks through the repository structure, identifying relevant files and their purposes.
2. **Language Detection**: Automatically detects programming languages based on file extensions.
3. **Code Understanding**: Utilizes GPT-4 to analyze code content and understand its purpose.
4. **Documentation Generation**: Creates a comprehensive README based on the analyzed information.

## Contributing

Feel free to contribute to this project by:
1. Implementing additional language support
2. Improving documentation quality
3. Adding new analysis features
4. Optimizing performance
