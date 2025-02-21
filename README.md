# AI README Generator

A tool for automatically generating README files for code repositories using LLM analysis.

## Overview

This tool analyzes a target repository and generates a README.md file through a series of AI prompts.
The system leverages LangChain and OpenAI's models to understand code structure, dependencies, and functionality.

## Key Components

- **Repository Analysis**: Scans repository structure, detects languages, entry points, and key files
- **Step-Based Processing**: Runs sequential prompts to generate different sections of documentation
- **Context Management**: Each step builds on previous steps' outputs for comprehensive documentation
- **Company-Specific Features**: Special handling for Gradle projects and Hobo deployments

## Technical Architecture

The project consists of three main components:

1. **Configuration Management** (`config.py`): Handles paths, command-line arguments and validation
2. **Repository Analyzer** (`analyzer.py`): Scans and analyzes repository structure  
3. **README Generator** (`readme_generator.py`): Orchestrates the generation process through steps

## Technical Details

### Repository Analysis

The analyzer detects:
- Programming languages and their distribution
- Entry points and executables
- Configuration files and dependencies
- Build systems (especially Gradle)
- Company-specific deployment tools (Hobo)

It specifically handles:
- Key project files (README, build configs, etc.)
- Non-empty existing READMEs
- READMEs in non-root locations
- Gradle wrapper detection with proper command suggestions

### Prompt Processing

The generator:
1. Reads prompt files in order (01-project-overview.md, 02-components-tech.md, etc.)
2. Creates context from previous steps
3. Applies repository analysis information
4. Generates section content
5. Combines sections into a final README
6. Cleans up intermediate files

## Requirements

- Python 3.10+
- OpenAI API key
- LangChain
- Pipenv

## Setup

1. Clone the repository:
   ```bash
   git clone git@code.corp.indeed.com:ai4dp/ai-readme-generation.git
   cd ai-readme-generator
   ```

2. Install dependencies:
   ```bash
   pipenv install
   ```

3. Create `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

Basic usage:
```bash
pipenv run python main.py -r /path/to/your/repository
```

Advanced options:
```bash
# Use a specific prompt collection
pipenv run python main.py -r /path/to/repo -c custom_prompts

# Start from a specific step
pipenv run python main.py -r /path/to/repo -s 3

# Run only a specific step
pipenv run python main.py -r /path/to/repo -s 5 -o

# Use a different AI model
pipenv run python main.py -r /path/to/repo -m gpt-4-turbo

# Keep intermediate output files
pipenv run python main.py -r /path/to/repo --keep-steps
```

| Option | Description |
|--------|-------------|
| `-r, --repo` | Target repository directory (required) |
| `-c, --collection` | Prompt collection to use (default: "default") |
| `-s, --step` | Step number to start from |
| `-o, --only` | Run only specific step |
| `-m, --model` | OpenAI model to use (default: "gpt-4o") |
| `--keep-steps` | Keep intermediate step output files after generation |

## How It Works

1. **Initialization**:
   - Parses arguments including the new `--keep-steps` flag
   - Creates configuration
   - Validates directories

2. **Repository Analysis**:
   - Checks for existing README
   - Analyzes file structure
   - Identifies languages and entry points
   - Detects Gradle and Hobo configuration

3. **Step Processing**:
   - Processes prompt files sequentially
   - Uses repository analysis as context
   - Generates section-specific content
   - Saves output to step files (named `step_XX_output.md`)

4. **README Compilation**:
   - Combines all step outputs
   - Uses LLM to structure and format
   - Adds AI-generated disclosure note
   - Writes final `ai.README.md`
   - Cleans up intermediate files (unless `--keep-steps` was specified)

The generator will automatically clean up the intermediate step files after generating the final README. If you need to retain these files for debugging or reference, use the `--keep-steps` flag.

## Customization

### Custom Prompt Collections

Create a new directory in `prompts/` with your custom prompts:
```
prompts/
  default/
    01-project-overview.md
    02-components-tech.md
    ...
  custom/
    01-my-custom-prompt.md
    ...
```

### Skip Specific Steps

Add `.SKIP.` to any prompt filename to skip that step:
```
03-architecture.SKIP.md
```

## Troubleshooting

- **API Key Issues**: Ensure your OpenAI API key is correctly set in `.env`
- **Model Selection**: For larger repositories, use models with higher context windows
- **Permission Errors**: Ensure write permissions in target output directory

## Development and Debugging

When developing or troubleshooting:

1. **Examining Intermediate Files**:
   - Use the `--keep-steps` flag to preserve step output files
   - Each step produces a separate markdown file in the `/output` directory
   - Files follow the naming convention `step_XX_output.md`

2. **Step Processing**:
   - Each prompt focuses on a specific aspect of the README
   - Step files show exactly what content was generated at each stage
   - Debugging individual steps can help identify issues in prompt design

3. **Understanding Cleanup**:
   - By default, intermediate files are removed after successful generation
   - The cleanup happens in the `cleanup_step_files()` method
   - Only files matching the pattern `step_*.output.md` are removed

If you're creating custom prompts or modifying the generator logic, keeping the intermediate files can help you understand how each step contributes to the final output.
