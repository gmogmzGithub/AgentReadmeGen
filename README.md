# AI README Generator

A tool that automatically generates README files for code repositories by analyzing codebases with Large Language Models (LLMs).

## Overview

The AI README Generator analyzes Java/Gradle/Spring Boot repositories to:
1. Understand project purpose and functionality
2. Determine how to run and configure the application
3. Generate comprehensive, usable README documentation
4. Optimize existing READMEs or create new ones from scratch
> Note: Currently focused on Java/Gradle/Spring Boot repositories. Support for additional languages is planned in upcoming releases.

It's specifically designed for Java Spring Boot projects but includes extensible support for other languages.

## Requirements

- API access to LLM services (via Indeed's internal LLM proxy)

## Installation

1. Clone the repository:
   ```bash
   git clone git@code.corp.indeed.com:ai4dp/ai-readme-generation.git
   cd ai-readme-generation
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp example.env .env
   ```

2. Obtain an API key from Indeed's LLM proxy:
   - Create/manage keys: https://llm-proxy.sandbox.indeed.net/manage/selfserve/createldapkeys
   - Add your key to the `.env` file

3. Ensure your `.env` contains:
   ```
   LLM_KEY=your_api_key_here
   LLM_KEY_ORGANIZATION=your_org_id_here
   OPENAI_BASE_URL=https://llm-proxy.sandbox.indeed.net/bedrock/v1/
   ```

## Supported Models

The application supports both Claude and OpenAI models:

- **Claude (Default)**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0` - Uses the `CLAUDE_BASE_URL` endpoint
- **OpenAI**: `gpt-4o` - Uses the `OPENAI_BASE_URL` endpoint

## Usage

### Quick Start

```bash
# Basic usage (uses Claude by default)
poetry run python src/main.py -r /path/to/your/repository

# Use GPT-4o instead of Claude
poetry run python src/main.py -r /path/to/repo -m gpt-4o

# Use a specific prompt collection
poetry run python src/main.py -r /path/to/repo -c custom_prompts

# Start from a specific step
poetry run python src/main.py -r /path/to/repo -s 3

# Run only a specific step
poetry run python src/main.py -r /path/to/repo -s 5 -o

# Keep intermediate output files
poetry run python src/main.py -r /path/to/repo --keep-steps

# Save intermediate files for debugging
poetry run python src/main.py -r /path/to/repo --save-intermediates
```

### Docker Usage

You can also run the tool in a Docker container:

```bash
# Build the Docker image
./build.sh

# Run the container on a local repository
./container-run.sh /path/to/repository
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-r, --repo` | Target repository directory (required) |
| `-c, --collection` | Prompt collection to use (default: "default") |
| `-s, --step` | Step number to start from |
| `-o, --only` | Run only specific step |
| `-m, --model` | Model to use (default: "us.anthropic.claude-3-5-sonnet-20241022-v2:0", options: "us.anthropic.claude-3-5-sonnet-20241022-v2:0", "gpt-4o") |
| `--keep-steps` | Keep intermediate step output files |
| `--language` | Force specific language analyzer (auto, java, python, javascript) |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |
| `--save-intermediates` | Save intermediate files for debugging |

## Sourcegraph Integration

This tool is designed to run as a batch operation on Sourcegraph, enabling automated README generation across multiple repositories.

### Deploying to Sourcegraph

1. Build and push the Docker image:
   ```bash
   ./build-and-push.sh
   ```
   Note: Update the version number in both `build-and-push.sh` and `batch-spec.yml` when making changes.

2. Configure the `batch-spec.yml` file to target the desired repositories.

3. Run the batch change from Sourcegraph.

### Troubleshooting Sourcegraph Deployments

If you encounter issues when running on Sourcegraph:

1. The Docker container may need specific environment adjustments. The `execute.sh` script has been modified to install dependencies at runtime to ensure compatibility.

2. Ensure path resolution is working correctly. The script sets `PYTHONPATH=/app` to help Python find modules correctly within the container.

3. Check that all required dependencies are available in the container. The `execute.sh` script installs packages from `requirements.frozen` at runtime.

## How It Works

The README generator uses a multi-step process to analyze code and generate documentation:

1. **Code Analysis**: Examines repository structure, detects framework usage (Spring Boot, Gradle), identifies entry points, configuration files, shell scripts, and more.

2. **Project Purpose Analysis (Step 1)**: Determines the core functionality and purpose of the application.

3. **Usage Instructions Generation (Step 2)**: Creates detailed instructions for running, configuring, and using the application.

4. **Draft README Creation (Step 3)**: Combines the previous analyses into a complete README draft.

5. **README Optimization (Step 4)**: Evaluates any existing README and decides whether to enhance it or replace it with the generated version.

The tool uses language-specific analyzers (currently Java-focused) to detect project structure and critical components.

## Architecture

The system consists of several key components:

- **Analyzers**: Language-specific modules that understand code structure.
  - `BaseAnalyzer`: Core analysis functionality
  - `JavaAnalyzer`: Java/Spring Boot/Gradle specific analysis
  - `CodeUnderstandingAnalyzer`: Focuses on purpose and functionality analysis

- **ReadmeGenerator**: Main orchestration class that manages the multi-step process.

- **Utilities**:
  - `CustomChatOpenAI`: Enhanced LLM integration that works with both OpenAI and Claude
  - `IntermediateFileManager`: Handles saving intermediate files for debugging
  - Various utility classes for file handling and analysis

- **Configuration**: Manages settings through the `GeneratorConfig` class.

## Prompt System

The generator uses a structured prompting system with four main steps:

1. **Project Purpose** (Step 1): Analyzes what the code does and who it's for
2. **Usage Instructions** (Step 2): Determines how to run, configure, and use the application
3. **Draft README** (Step 3): Creates a complete README document
4. **Final README** (Step 4): Optimizes based on any existing README content

Each step builds on the previous ones, with the LLM receiving carefully structured context about the repository.

### Extending Language Support

The system can be extended to support other languages by creating additional analyzer classes similar to JavaAnalyzer. The BaseAnalyzer provides core functionality that can be inherited and specialized. Implementation of Python and JavaScript analyzers is scheduled for upcoming commits.

## Output and Artifacts

By default, the tool generates:

- `README.md` in the target repository directory

With `--save-intermediates` flag, it also saves:
- Step outputs: Files showing the output of each generation step
- Context files: JSON files with the context provided to the LLM
- Prompt files: The actual prompts sent to the LLM

## Support

For questions or issues:
- For LLM proxy access issues, reach out in #help-llm
- For application issues, create a ticket or contact the AI4DP team

## Development

### Future Enhancements

- Add support for Python and JavaScript projects

#### Nice to haves for upcoming changes
- Extract repository ownership information and include it in the generated README
- Improve detection of project dependencies and requirements
- Enhance the ability to understand API endpoints and documentation