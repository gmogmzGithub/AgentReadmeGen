"""Main README generator implementation with enhanced logging."""

import os
import logging
import re
from pathlib import Path
from typing import List

from src.config import GeneratorConfig
from src.analyzers.base_analizer import BaseAnalyzer

from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain.memory import SimpleMemory
from src.utils import CustomChatOpenAI
from src.utils.intermediate_file_manager import IntermediateFileManager


class ReadmeGenerator:
    """Generates README documentation using AI-powered prompts with code understanding."""

    STEP_PROMPTS = {
        1: """
        # Repository Analysis Information
        Repository Name: ${name}
        Primary Language: ${language}
        ${is_spring_boot}

        # Code Analysis
        ${formatted_analysis}
        ${entry_points}
        ${key_components}

        # Key Files Content
        ${key_files_content}

        # Your Task
        Analyze this repository and determine its specific purpose.

        Focus on:
        1. What problem does this code solve?
        2. What is the main functionality (not the technical implementation)?
        3. Who would use this code and why?

        Write a clear, concise explanation (3-5 sentences) of the repository's purpose that provides technical developers with an immediate understanding of what this codebase does.

        DO NOT list repository contents, structure, or implementation details.
        DO NOT include technical jargon without explanation.
        """,
        2: """
        # Repository Context

        # Repository Analysis Information
        Repository Name: ${name}
        Primary Language: ${language}
        ${is_spring_boot}
        ${build_system}

        # Configuration Files
        ${config_files}

        # Run Commands and Scripts
        ${shell_scripts}
        ${root_shell_scripts}
        ${run_commands}

        ## Script Analysis
        - **Root Directory Scripts**: Analyze any .sh files in the repository root carefully - these often contain custom commands to run the application with Gradle or perform other essential operations.
          - Scripts containing 'start', 'run', or 'up' in their name typically launch the application
          - Scripts with 'stop', 'down', or 'kill' typically terminate the application

        - **Docker Configuration**: When Dockerfile or docker-compose.yml files exist:
          - Check for custom entry points or commands
          - Note any environment variables that must be set
          - Look for volume mounts that indicate where configuration files should be placed

        - **Example Files**: Look for .example or .template files as they demonstrate:
          - Required configuration settings
          - Environment variables needed to run the application
          - Format for any custom config files

        # Your Task
        Create comprehensive, practical usage instructions for this repository.

        Focus on:
        1. How to run the application locally (with exact commands)
        2. How to deploy the application (if deployment information is available)
        3. Required configuration settings and environment variables

        Don't include the following:
        - git clone or git checkout commands.

        Format your instructions as a clear, sequential guide that a new developer could follow.
        Include actual commands where possible and explain what each command does.
        """,
        3: """
        # README Generation Task

        ## Previous Analysis Results
        ### Repository Purpose
        ${project_purpose}

        ### Getting Started
        ${usage_instructions}

        ## Repository Information
        Repository Name: ${name}
        Primary Language: ${language}
        ${is_spring_boot}
        ${build_system}

        ## Your Task
        Create a comprehensive, professional README.md file for this repository by combining the purpose analysis and usage instructions provided above.  Try to adhere to their information and format as much as possible, while achieving the overall format listed below.

        The README should include:

        1. Title
        2. Intro / Summary
            - What the project does
            - Purpose and core functionality
            - Should be drawn from the "Repository Purpose" section above.
        3. Installation / Getting Started
            - Should be drawn from the "Getting Started" section above.
            - Do not add additional pre-requisites that are not listed in the previous analysis results section.

        Use the information already gathered above as authoritative.  Don't add additional information not contained in the previous analysis results section.

        Format the README using proper Markdown syntax with appropriate headings, code blocks, and formatting. Make it visually clear and easy to navigate.

        DO NOT include placeholder text or TODO items. If information is missing for a standard section, omit that section rather than including incomplete information.

        The README should be complete and immediately usable without further editing.

        DO NOT include any of the following information:
        - deployment information.  Only focus on local development.
        - monitoring
        - logging
        """,
        4: """
            # README Optimization Task

            ## README Evaluation
            Recommendation: ${readme_recommendation}

            Evaluation Summary:
            ${readme_evaluation}

            ## Original README Content
            ```markdown
            ${original_readme}
            ```

            ## AI-Generated README Content (Step 3)
            ```markdown
            ${generated_readme}
            ```

            ## Your Task
            Create an optimized final README based on the evaluation results.

            Follow this specific guidance:

            1. If recommendation is "OVERWRITE":
               - Use the AI-generated README as your complete replacement
               - Remove any TODO markers, template instructions, or placeholder text
               - Preserve any specific unique information from the original if it exists (e.g., specific configuration details that aren't in the generated version)

            2. If recommendation is "RESPECT_ORIGINAL":
               - Use the original README as your base
               - Enhance it with any missing information from the AI-generated version
               - Maintain the original structure and style where possible
               - Remove any TODO markers or placeholder text that might still exist
               - Ensure all information is up-to-date and accurate

            IMPORTANT GUIDELINES:
            - Never include TODO markers in the final README
            - Never include template instructions like "Write a meaningful README.md for your daemon"
            - Never include `### Prerequisites` sections
            - Never include `### Troubleshooting` sections
            - Never include `./gradlew assemble` command, we only use `./gradlew build` for building or `./gradlew run` for running the application
            - Always provide complete, usable instructions rather than placeholders
            - Ensure the final README clearly explains what the project does and how to use it
            - If the original has valuable content about project-specific configurations, preserve it

            The final README should:
            - Use proper Markdown formatting with appropriate headings and sections
            - Be complete and immediately usable without placeholders or TODOs
            - Maintain accurate technical information about the repository
            - Focus on clarity and usefulness for developers

            Document your reasoning (as comments at the end of the output):
            - The reasoning should be on HTML comments at the end of the output, for example:
                - <!-- Your reasoning
                        Your reasoning
                        Your reasoning 
                 -->
            - Briefly explain your approach to creating the final README
            - Note key decisions made when merging or replacing content
            - Justify why certain sections were preserved, enhanced, or replaced
            """,
    }

    STEP_NAMES = {
        1: "project-purpose",
        2: "usage-instructions",
        3: "draft-readme",
        4: "final-readme",
    }

    def __init__(self, config: GeneratorConfig, analyzer: BaseAnalyzer = None) -> None:
        """Initialize the README generator."""
        self.config = config
        self.analyzer = analyzer

        if self.analyzer is None:
            from src.analyzers import get_analyzer_for_repo

            self.analyzer = get_analyzer_for_repo(config)

        self.llm = CustomChatOpenAI(model=config.model, temperature=0)
        self._has_checked_skipped = False
        self.logger = logging.getLogger("ReadmeGenerator")

        # Extract model identifier
        self.model_identifier = self._get_model_identifier()

        self.file_manager = IntermediateFileManager(config)

    def _get_model_identifier(self) -> str:
        """Return the exact model string as provided in the config.

        Returns:
            The exact model identifier string
        """
        return self.config.model

    def extract_step_number(self, filename: Path | str) -> int:
        """Extract step number from filename.

        Args:
            filename: Path or string representing the filename

        Returns:
            Integer step number, or 0 if invalid
        """
        try:
            if isinstance(filename, str):
                name = Path(filename).stem
            else:
                name = filename.stem

            # Look for a two-digit number at the start
            match = re.match(r"^(\d{2})-", name)
            if match:
                return int(match.group(1))
            return 0
        except (ValueError, TypeError, AttributeError):
            return 0

    def find_step_files(self) -> List[Path]:
        """Find all valid step files in the prompts directory.

        Returns:
            List of valid step file paths
        """
        # Get all potential step files (with numeric prefix)
        step_files = [
            f
            for f in self.config.prompts_dir.glob("[0-9][0-9]-*.md")
            if self.extract_step_number(f) > 0
        ]

        # Filter out .SKIP files
        valid_files = [f for f in step_files if ".SKIP." not in f.name]

        # Sort by step number
        valid_files.sort(key=lambda f: self.extract_step_number(f))

        self.logger.info(f"Found {len(valid_files)} valid step files")
        return valid_files

    def get_output_path(self, step_num: int) -> Path:
        """Get the output file path for a given step."""
        return self.config.output_dir / f"step_{step_num:02d}_output.md"

    def prepare_context(self, current_step: int) -> str:
        """Prepare context by concatenating previous step outputs.

        Args:
            current_step: Current step number being processed

        Returns:
            Combined context from all previous steps
        """
        if current_step <= 1:
            # No previous steps for context
            return ""

        # Collect outputs from previous steps, skipping any that don't exist
        outputs = []
        for i in range(1, current_step):
            output_file = self.get_output_path(i)
            if output_file.exists() and output_file.stat().st_size > 0:
                outputs.append(output_file.read_text())
                self.logger.debug(f"Added context from step {i}")

        # Return combined outputs
        combined = "\n\n".join(outputs)
        self.logger.debug(f"Prepared context with {len(outputs)} previous steps")
        return combined

    def process_prompt(self, step_num: int) -> bool:
        """Process a prompt for a specific step."""
        if step_num not in self.STEP_PROMPTS:
            self.logger.error(f"Invalid step number: {step_num}")
            return False

        output_file = self.get_output_path(step_num)
        step_name = self.STEP_NAMES.get(step_num, f"step-{step_num}")

        self.logger.info(f"Processing step {step_num}: {step_name}")

        # Check if we have repository context
        if not hasattr(self, "repo_context"):
            self.logger.error("Repository context missing. Run analysis first.")
            return False

        # Prepare enhanced context for this step using our improved method
        enhanced_context = self.prepare_enhanced_context(self.repo_context, step_num)

        repo_name = self.repo_context.get("name", "unknown_repo")
        self.file_manager.save_context(
            repo_name, step_num, step_name, enhanced_context, self.model_identifier
        )

        # Pass the step number to the format method
        full_prompt = self._format_context_for_prompt(enhanced_context, step_num)

        self.file_manager.save_prompt(
            repo_name, step_num, step_name, full_prompt, self.model_identifier
        )

        # Additional logging only when saving intermediates is enabled
        if self.config.save_intermediates:
            self.logger.info(
                f"Prompt contains original README: {'${original_readme}' not in full_prompt}"
            )
            self.logger.info(
                f"Prompt contains generated README: {'${generated_readme}' not in full_prompt}"
            )

        # Call the LLM
        response = self.llm.invoke(full_prompt)

        # Extract output content
        output_content = response.content

        if step_num == 4:
            from src.utils.readme_utils import extract_reasoning

            # Extract reasoning
            output_content_cleaned, reasoning_text = extract_reasoning(output_content)

            # Write cleaned output to output file
            output_file.write_text(output_content_cleaned)

            # Write reasoning to separate file
            reasoning_file = self.config.output_dir / "reasoning.md"
            reasoning_file.write_text(reasoning_text)

            self.logger.info(f"Extracted reasoning and saved to {reasoning_file}")

            # Save a copy of the reasoning
            if self.config.save_intermediates:
                reasoning_filename = f"{repo_name}_step{step_num}_{step_name}_reasoning_{self.model_identifier}.md"
                reasoning_path = self.config.intermediates_dir / reasoning_filename

                with open(reasoning_path, "w", encoding="utf-8") as f:
                    f.write(reasoning_text)

                self.logger.info(f"Reasoning saved to: {reasoning_path}")
        else:
            # For other steps, just write the output as usual
            output_file.write_text(output_content)

        # Save a copy of the step output using the file manager
        self.file_manager.save_step_output(
            repo_name,
            step_num,
            step_name,
            output_content_cleaned if step_num == 4 else output_content,
            self.model_identifier,
        )

        self.logger.info(f"Successfully processed step {step_num}")
        return True

    def _log_repository_details(self, repo_context):
        """Log detailed information about the analyzed repository.

        Args:
            repo_context: Dictionary containing repository analysis information
        """
        self.logger.debug("Repository analysis completed")
        self.logger.info(f"Repository name: {repo_context.get('name', 'Unknown')}")
        self.logger.info(
            f"Primary language: {repo_context.get('primary_language', 'Unknown')}"
        )
        self.logger.info(f"Total files: {repo_context.get('total_files', 0)}")

        # Log Spring Boot detection if applicable
        if repo_context.get("has_spring_boot", False):
            self.logger.info(
                "Spring Boot application detected - treating as Java project"
            )

        # Log shell scripts information
        root_shell_scripts = repo_context.get("root_shell_scripts", [])
        if root_shell_scripts:
            self.logger.info(f"Root shell scripts found: {len(root_shell_scripts)}")
            for script in root_shell_scripts:
                self.logger.info(f"  - Root script: {script}")
            if len(root_shell_scripts) > 5:
                self.logger.info(
                    f"  - ... and {len(root_shell_scripts) - 5} more root scripts"
                )

        # Log build system commands
        build_system = repo_context.get("build_system", {})
        if build_system and build_system.get("commands"):
            self.logger.info("Build system commands:")
            for cmd_name, cmd_value in build_system.get("commands", {}).items():
                if isinstance(cmd_value, list):
                    for cmd in cmd_value:
                        self.logger.info(f"  - {cmd_name}: {cmd}")
                else:
                    self.logger.info(f"  - {cmd_name}: {cmd_value}")

        # Log entry points
        entry_points = repo_context.get("entry_points", [])
        if entry_points:
            self.logger.info(f"Entry points found: {len(entry_points)}")
            for ep in entry_points:
                self.logger.info(f"  - {ep}")
            if len(entry_points) > 5:
                self.logger.info(f"  - ... and {len(entry_points) - 5} more")
        else:
            self.logger.info("No entry points found")

        entry_points = repo_context.get("entry_points", [])
        if entry_points:
            self.logger.info(f"Entry points found: {len(entry_points)}")
            for ep in entry_points:  # Log first 5 entry points
                self.logger.info(f"  - {ep}")
            if len(entry_points) > 5:
                self.logger.info(f"  - ... and {len(entry_points) - 5} more")
        else:
            self.logger.info("No entry points found")

    def run(self) -> None:
        """Main execution flow using only the integrated prompts."""
        try:
            self.config.validate()

            # Create output directory if it doesn't exist
            self.config.output_dir.mkdir(exist_ok=True, parents=True)

            os.chdir(self.config.target_repo)

            # Get repository context
            self.repo_context = self.analyzer.analyze_repository()

            # Log repository details
            self._log_repository_details(self.repo_context)

            self.file_manager.save_repo_context(
                self.repo_context, self.model_identifier
            )

            # Define the steps to process (all steps by default)
            all_steps = sorted(list(self.STEP_PROMPTS.keys()))

            # Determine which steps to process based on configuration
            if self.config.only_mode:
                if self.config.start_step is None:
                    raise ValueError("--only must be used with --step")
                if self.config.start_step not in all_steps:
                    self.logger.error(f"Invalid step number: {self.config.start_step}")
                    return
                steps_to_process = [self.config.start_step]
            elif self.config.start_step is not None:
                # Start from the specified step
                if self.config.start_step not in all_steps:
                    self.logger.error(f"Invalid step number: {self.config.start_step}")
                    return
                start_index = all_steps.index(self.config.start_step)
                steps_to_process = all_steps[start_index:]
            else:
                # Check for last completed step
                last_completed = self.get_last_completed_step()
                if last_completed > 0 and last_completed in all_steps:
                    start_index = all_steps.index(last_completed) + 1
                    if start_index < len(all_steps):
                        steps_to_process = all_steps[start_index:]
                    else:
                        # All steps are already completed
                        self.logger.info("All steps already completed")
                        return
                else:
                    # Start from the beginning
                    steps_to_process = all_steps

            self.logger.info(f"Processing steps: {steps_to_process}")

            # Process each step
            failed_steps = []
            for step_num in steps_to_process:
                if not self.process_prompt(step_num):
                    self.logger.warning(f"Failed to process step {step_num}")
                    failed_steps.append(step_num)

            # Log results
            if failed_steps:
                self.logger.warning(f"The following steps failed: {failed_steps}")
            else:
                self.logger.info("All steps processed successfully")

            # Finalize README - Copy final output to intermediates directory and
            # save as README.md
            final_step = max(self.STEP_PROMPTS.keys())
            final_output = self.get_output_path(final_step)

            if final_output.exists():
                repo_name = self.repo_context.get("name", "unknown_repo")
                readme_content = final_output.read_text(encoding="utf-8")

                # Save final README using the file manager (this will save to README.md)
                self.file_manager.save_final_readme(
                    repo_name, readme_content, self.model_identifier
                )

            # Clean up step files if configured, but only in the output directory
            if not self.config.keep_steps:
                self.cleanup_step_files()

        except Exception as e:
            self.logger.error(f"Error during execution: {e}")
            raise

    def cleanup_step_files(self) -> None:
        """Remove all intermediate step output files after final README generation."""
        try:
            step_files = list(self.config.output_dir.glob("step_*_output.md"))
            if not step_files:
                self.logger.info("No step files to clean up")
                return

            # Remove each file from the output directory only
            for file in step_files:
                try:
                    file.unlink()
                    self.logger.info(f"Removed intermediate file: {file}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove {file}: {e}")

            self.logger.info(
                f"Successfully cleaned up {len(step_files)} intermediate files from output directory"
            )

            # Only log about preserved files if they were actually saved
            if self.config.save_intermediates:
                self.logger.info(
                    f"Step output files preserved in {self.config.intermediates_dir} directory"
                )

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def save_repo_context_json(self, repo_context):
        """Save the repository context information as a JSON file."""
        # Only save if save_intermediates is enabled
        if not self.config.save_intermediates:
            return

        import json
        from datetime import datetime

        try:
            intermediates_dir = self.config.intermediates_dir

            repo_name = repo_context.get("name", "unknown_repo")
            filename = f"{repo_name}_repo_context_{self.model_identifier}.json"

            json_path = intermediates_dir / filename

            clean_context = {}
            for key, value in repo_context.items():
                if key in ["files", "sorted_files"]:
                    clean_context[key] = []
                    for file_info in value:
                        file_copy = {
                            k: v for k, v in file_info.items() if k != "content"
                        }
                        clean_context[key].append(file_copy)
                else:
                    clean_context[key] = value

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(clean_context, f, indent=2, default=str)

            self.logger.info(f"Repository context saved to: {json_path}")

        except Exception as e:
            self.logger.error(f"Error saving repository context JSON: {e}")

    """Improved context builder for the README generator LLM prompts."""

    def prepare_enhanced_context(self, repo_context, step_num=None):
        """
        Prepare optimized context for LLM consumption based on the current step.

        Args:
            repo_context: Complete repository analysis context
            step_num: Current processing step number (optional)

        Returns:
            Dictionary with structured context optimized for LLM prompt
        """
        # Create the base context
        base_context = {
            "name": repo_context.get("name", "Unknown Project"),
            "language": repo_context.get("primary_language", "Unknown"),
            "is_spring_boot": repo_context.get("has_spring_boot", False),
            "entry_points": repo_context.get("entry_points", []),
            "build_system": repo_context.get("build_system", {}).get("type", "unknown"),
            "custom_tools": repo_context.get("custom_tools", {}).get(
                "custom_tools", []
            ),
            "formatted_analysis": repo_context.get("formatted_analysis", ""),
            "file_breakdown": repo_context.get("file_breakdown", {}),
        }

        # Add shell scripts information if available
        shell_scripts = []
        if "shell_scripts" in repo_context:
            shell_scripts.extend(repo_context.get("shell_scripts", []))
        if "root_shell_scripts" in repo_context:
            shell_scripts.extend(repo_context.get("root_shell_scripts", []))

        base_context["shell_scripts"] = shell_scripts

        # Add existing README content if available
        if "readme_contents" in repo_context and repo_context["readme_contents"]:
            base_context["existing_readme"] = repo_context["readme_contents"]

        # Step-specific context enrichment
        if step_num == 1:  # Project Purpose
            # For step 1, focus on key files and code structure
            return self._build_step1_context(base_context, repo_context)
        elif step_num == 2:  # Usage Instructions
            # For step 2, focus on configuration and execution
            return self._build_step2_context(base_context, repo_context)
        elif step_num == 3:  # Final README
            # For step 3, include all previous outputs and comprehensive information
            return self._build_step3_context(base_context, repo_context)
        elif step_num == 4:  # Optimized Final README
            # For step 4, compare original with generated README
            return self._build_step4_context(base_context, repo_context)

        # Default case: return base context with formatted analysis
        return base_context


    async def _is_crappy_readme(self, readme_content, generated_readme):
        """
        Uses the LLM to determine if a README follows patterns of crappy READMEs.

        Args:
            readme_content: The original README content
            generated_readme: The AI-generated README content

        Returns:
            tuple: (is_crappy, response_text)
                - is_crappy: boolean indicating if the README should be overwritten
                - response_text: The full explanation from the LLM
        """
        # Skip evaluation if README is empty or minimal
        if (
            not readme_content
            or readme_content.strip() == "No original README found."
            or len(readme_content.strip()) < 20
        ):
            return True, "README is empty or minimal"

        # Prepare the evaluation prompt
        evaluation_prompt = """
    # README Evaluation Task

    Your task is to evaluate if an original README is of poor quality and should be replaced with an AI-generated version.

    ## Examples of Low-Quality READMEs

    These are examples of low-quality READMEs that should be replaced:

    EXAMPLE 1:
    ```
    # skeleton-spring-boot-daemon

    - **TODO:** Read the [Spring Boot skeleton instructions wiki page](https://go.com/spring-boot-skeleton-main#BasicDaemon) for basic setup instructions and common questions. 
    - **TODO:** Write a meaningful README.md for your daemon:
        - Describe what the daemon does
        - Mention any dependencies that need to be setup before running the daemon


     ### Secrets at dev time
      --------------------------------
     - Copy the 'application-env-local.yml.example' file.
     - Rename it to 'application-env-local.yml'
     - Fill in the credentials (if necessary otherwise you may remove them).
     - Add any additional properties.
    ```

    EXAMPLE 2:
    ```
    [Goggles](https://wiki.com/display/AGGC/Goggles): PDF/JSON to HTML converter HTTP service.
    ```

    EXAMPLE 3:
    ```
    # he-billing-reporting-service

    Hiring Event Billing Reporting service

    ## TODO: Additional project setup ##
    *You may delete this section after following the instructions below.*

      - Read [Setting up a new Java/Kotlin GraphQL API using the Golden Path](https://wiki.com/pages/viewpage.action?pageId=534351928)
        for complete details on setting up your Marvin deployments and configuring GitLab CI/CD.
    - **TODO: OneGraph integration**
        - Once you have created a Marvin project and deployment group in QA, set `LEMMA: "true"` in `.gitlab-ci.yml` to run Lemma.
    ...
    ```

    ## Common Issues in Low-Quality READMEs:

    1. Contains TODO markers
    2. Contains template instructions (e.g., "Write a meaningful README")
    3. Contains placeholder text (e.g., "Describe what the daemon does")
    4. References skeleton templates or setup instructions
    5. Is extremely brief (just a link or one-line description)
    6. Has section titles with minimal content
    7. Consists primarily of generic setup instructions
    8. Lacks actual project description and usage information

    ## Original README to Evaluate:
    ```
    {readme_content}
    ```

    ## AI-Generated Replacement:
    ```
    {generated_readme}
    ```

    ## Your Task:
    Based on the examples and common issues, evaluate if the original README should be replaced with the AI-generated version.

    Specifically:
    1. Does the original README match patterns of low-quality READMEs?
    2. Does it contain TODOs, placeholders, or template instructions?
    3. Does it lack substantial information about what the project does and how to use it?
    4. Does the AI-generated version provide significantly better information?

    Answer "YES" if the original README should be replaced, or "NO" if it contains meaningful, project-specific content that should be preserved.

    First, provide a brief analysis of the specific issues with the original README.
    Then, provide your final answer as either "YES" or "NO" on a separate line.
    """

        evaluation_prompt = evaluation_prompt.format(
            readme_content=readme_content, generated_readme=generated_readme
        )

        try:
            # Call the LLM to evaluate the README
            response = self.llm.invoke(evaluation_prompt)
            response_text = response.content

            # Extract the answer (YES or NO)
            # Look for YES or NO at the end of the response or on its own line
            lines = response_text.strip().split("\n")
            final_line = lines[-1].strip().upper()

            if "YES" in final_line and "NO" not in final_line:
                return True, response_text
            elif "NO" in final_line and "YES" not in final_line:
                return False, response_text

            # If not clear from the final line, check the whole response
            if (
                "YES" in response_text.upper()
                and "SHOULD BE REPLACED" in response_text.upper()
            ):
                return True, response_text
            else:
                return False, response_text

        except Exception as e:
            self.logger.error(f"Error evaluating README: {e}")
            # Default to preserving the original README in case of error
            return False, f"Error during evaluation: {str(e)}"

    def _build_step1_context(self, base_context, repo_context):
        """Build context for Step 1: Project Purpose."""
        step_context = base_context.copy()

        # Add brief analysis only if non-empty
        formatted_analysis = repo_context.get("formatted_analysis", "").strip()
        if formatted_analysis:
            step_context["brief_analysis"] = formatted_analysis

        # Prioritize key files - entry points, main classes, and build files
        key_paths = set()

        # Add entry points only if non-empty
        entry_points = repo_context.get("entry_points", [])
        if entry_points:
            key_paths.update(entry_points)

        # Add key project files only if non-empty
        key_project_files = repo_context.get("key_project_files", [])
        if key_project_files:
            key_paths.update(key_project_files)

        # Add top important files by score
        for file_info in repo_context.get("files", [])[:35]:
            if "path" in file_info:
                key_paths.add(file_info["path"])

        # Add file contents for key files, but skip empty files
        key_files_content = {}
        for path in key_paths:
            content = repo_context.get("file_contents", {}).get(path, "")
            if content and content.strip():  # Only add non-empty files
                key_files_content[path] = content

        # Only add key_files_content if there are any files with content
        if key_files_content:
            step_context["key_files_content"] = key_files_content

        return step_context

    def _build_step2_context(self, base_context, repo_context):
        """Build context for Step 2: Usage Instructions with critical information.

        This context focuses on all elements needed to understand how to run and deploy
        the application, including entry points, build commands, and configuration.
        """
        step_context = base_context.copy()

        # CRITICAL: Always include entry points - these are essential for running the app
        entry_points = repo_context.get("entry_points", [])
        if entry_points:
            step_context["entry_points"] = entry_points

            # Also add content of entry point files as they often contain critical info
            for entry_point in entry_points:
                content = repo_context.get("file_contents", {}).get(entry_point, "")
                if content and content.strip():
                    if "key_files_content" not in step_context:
                        step_context["key_files_content"] = {}
                    step_context["key_files_content"][entry_point] = content

        # CRITICAL: Main build.gradle file is essential for understanding how to build/run
        build_gradle_path = "build.gradle"
        build_gradle_content = repo_context.get("file_contents", {}).get(
            build_gradle_path, ""
        )
        if build_gradle_content and build_gradle_content.strip():
            if "key_files_content" not in step_context:
                step_context["key_files_content"] = {}
            step_context["key_files_content"][build_gradle_path] = build_gradle_content

        if docker_compose_content and docker_compose_content.strip():
            if "key_files_content" not in step_context:
                step_context["key_files_content"] = {}
            step_context["key_files_content"][
                docker_compose_path
            ] = docker_compose_content

        # Add any controllers that might have REST endpoints - useful for API usage
        for path, content in repo_context.get("file_contents", {}).items():
            if "controller" in path.lower() and content and content.strip():
                if "key_files_content" not in step_context:
                    step_context["key_files_content"] = {}
                step_context["key_files_content"][path] = content

        # Add configuration files - but only non-empty ones
        config_files = []
        for path in repo_context.get("config_files", [])[:10]:  # Limit to top 10
            content = repo_context.get("file_contents", {}).get(path, "")
            if content and content.strip():  # Only add non-empty files
                config_files.append(
                    {
                        "path": path,
                        "content": content,
                    }
                )

        # Only add config_files to step_context if there are any
        if config_files:
            step_context["config_files"] = config_files

        # Example configs - only non-empty ones but critical for deployment
        example_configs = []
        for path in repo_context.get("example_config_files", []):
            content = repo_context.get("file_contents", {}).get(path, "")
            if content and content.strip():  # Only add non-empty files
                example_configs.append(
                    {
                        "path": path,
                        "content": content,
                    }
                )

        # Only add example_configs to step_context if there are any
        if example_configs:
            step_context["example_configs"] = example_configs


        # Filter out empty command sections and only add if there are actual commands
        run_commands = {}

        build_commands = repo_context.get("build_system", {}).get("commands", {})
        if build_commands:
            filtered_build_commands = {}
            for cmd_type, cmds in build_commands.items():
                if cmds:  # Only add non-empty command sections
                    filtered_build_commands[cmd_type] = cmds
            if filtered_build_commands:
                run_commands["build"] = filtered_build_commands

        # Only add run_commands if there are any real commands
        if run_commands:
            step_context["run_commands"] = run_commands

        # CRITICAL: Add standard gradle commands even if none were explicitly detected
        if "run_commands" not in step_context or not step_context.get(
            "run_commands", {}
        ).get("build"):
            # Since we know this is a Gradle project with Spring Boot, add standard commands
            standard_commands = {"build": {"gradle": ["./gradlew build"]}}

            # Check if we have a mainClass in build.gradle to add run command
            if build_gradle_content and "mainClass" in build_gradle_content:
                standard_commands["build"]["run"] = ["./gradlew run"]

            step_context["run_commands"] = standard_commands

        # Shell scripts - only add non-empty lists
        shell_scripts = repo_context.get("shell_scripts", [])
        if shell_scripts:
            step_context["shell_scripts"] = shell_scripts

        root_shell_scripts = repo_context.get("root_shell_scripts", [])
        if root_shell_scripts:
            step_context["root_shell_scripts"] = root_shell_scripts

        # Add formatted analysis only if non-empty
        formatted_analysis = repo_context.get("formatted_analysis", "").strip()
        if formatted_analysis:
            step_context["brief_analysis"] = formatted_analysis

        # CRITICAL: Include Spring Boot indicator if applicable
        if repo_context.get("has_spring_boot", False):
            step_context["is_spring_boot"] = True


        return step_context

    def _build_step3_context(self, base_context, repo_context):
        """Build context for Step 3: Final README."""
        step_context = base_context.copy()

        # Get previous steps' outputs
        previous_steps = self._gather_previous_steps_output(3)

        # Only add project purpose if it exists and is non-empty
        project_purpose = previous_steps.get(1, "").strip()
        if project_purpose:
            step_context["project_purpose"] = project_purpose

        # Only add usage instructions if they exist and are non-empty
        usage_instructions = previous_steps.get(2, "").strip()
        if usage_instructions:
            step_context["usage_instructions"] = usage_instructions

        # Limit to top 20 dependencies and filter out empty ones
        dependencies = [
            dep
            for dep in repo_context.get("dependencies", [])[:20]
            if dep and dep.strip()
        ]
        if dependencies:
            step_context["dependencies"] = dependencies

        # Add formatted analysis only if non-empty
        formatted_analysis = repo_context.get("formatted_analysis", "").strip()
        if formatted_analysis:
            step_context["formatted_analysis"] = formatted_analysis

        # Only create entry_points_formatted if there are actual entry points
        entry_points = repo_context.get("entry_points", [])
        if entry_points:
            step_context["entry_points_formatted"] = "\n".join(
                [f"- {ep}" for ep in entry_points]
            )

        # Get key paths and filter for non-empty content
        key_paths = set()

        # Add entry points only if non-empty
        if entry_points:
            key_paths.update(entry_points)

        # Add key project files only if non-empty
        key_project_files = repo_context.get("key_project_files", [])
        if key_project_files:
            key_paths.update(key_project_files)

        # Add top files
        for file_info in repo_context.get("files", [])[:10]:  # Limit to top 10
            if "path" in file_info:
                key_paths.add(file_info["path"])

        # Add file contents for key files, but skip empty files
        key_files_content = {}
        for path in key_paths:
            content = repo_context.get("file_contents", {}).get(path, "")
            if content and content.strip():  # Only add non-empty files
                key_files_content[path] = content

        # Only add key_files_content if there are any files with content
        if key_files_content:
            step_context["key_files_content"] = key_files_content

        return step_context

    def _build_step4_context(self, base_context, repo_context):
        """Build context for Step 4: README Optimization with LLM evaluation."""
        step_context = base_context.copy()

        # Get the AI-generated README from step 3
        step3_output = self.get_output_path(3)
        generated_readme = ""
        if step3_output.exists() and step3_output.stat().st_size > 0:
            generated_readme = step3_output.read_text()

        # Clean up any markdown code fences in the generated README
        if generated_readme.startswith("```") and "```" in generated_readme[3:]:
            # If it starts with markdown code fences, extract the content between them
            if generated_readme.startswith("```markdown"):
                start_pos = generated_readme.find("\n", 10) + 1
            else:
                start_pos = generated_readme.find("\n", 3) + 1

            end_pos = generated_readme.rindex("```")
            if start_pos > 0 and end_pos > start_pos:
                generated_readme = generated_readme[start_pos:end_pos].strip()

        step_context["generated_readme"] = generated_readme

        # Get the original README content
        original_readme = ""

        # Handle the case when readme_contents is a dictionary (most common format)
        if isinstance(repo_context.get("readme_contents", {}), dict):
            for path, content in repo_context["readme_contents"].items():
                if path.lower() in [
                    "readme.md",
                    "readme",
                    "read.me",
                ] or path.lower().endswith("/readme.md"):
                    original_readme = content
                    break

        # Also check if there's a direct "original_readme" key
        elif "original_readme" in repo_context:
            original_readme = repo_context["original_readme"]

        # If we still don't have content but have "existing_readme", use that
        elif "existing_readme" in repo_context:
            if isinstance(repo_context["existing_readme"], dict):
                for path, content in repo_context["existing_readme"].items():
                    if path.lower() in [
                        "readme.md",
                        "readme",
                        "read.me",
                    ] or path.lower().endswith("/readme.md"):
                        original_readme = content
                        break
            elif isinstance(repo_context["existing_readme"], str):
                original_readme = repo_context["existing_readme"]

        # Set a default if no README was found
        if not original_readme or not original_readme.strip():
            original_readme = "No original README found."

        step_context["original_readme"] = original_readme

        # Use a synchronous wrapper for the async evaluation method
        import asyncio

        try:
            is_crappy, evaluation = asyncio.run(
                self._is_crappy_readme(original_readme, generated_readme)
            )
        except Exception as e:
            self.logger.error(f"Error running README evaluation: {e}")
            # Default to preserving the original README in case of error
            is_crappy, evaluation = False, "Error during evaluation"

        step_context["is_crappy_readme"] = is_crappy
        step_context["readme_evaluation"] = evaluation

        # Add a clear recommendation
        if is_crappy:
            step_context["readme_recommendation"] = "OVERWRITE"
        else:
            step_context["readme_recommendation"] = "RESPECT_ORIGINAL"

        # Log the README assessment
        self.logger.info(
            f"README assessment: {'OVERWRITE' if is_crappy else 'RESPECT_ORIGINAL'}"
        )

        # Log the content lengths
        self.logger.debug(f"Original README length: {len(original_readme)}")
        self.logger.debug(f"Generated README length: {len(generated_readme)}")

        return step_context

    def _gather_previous_steps_output(self, current_step):
        """
        Gather outputs from previous steps.

        Args:
            current_step: Current step number

        Returns:
            Dictionary mapping step numbers to their output content
        """
        outputs = {}
        for i in range(1, current_step):
            output_file = self.get_output_path(i)
            if output_file.exists() and output_file.stat().st_size > 0:
                outputs[i] = output_file.read_text()
        return outputs

    def create_readme_step_chain(self, step_num, context):
        """
        Create a LangChain for a specific README generation step using integrated prompts.

        Args:
            step_num: Step number to process
            context: Enhanced context for this step

        Returns:
            Configured LangChain ready to execute
        """
        # Get the prompt template for this step from our integrated prompts
        if step_num not in self.STEP_PROMPTS:
            self.logger.error(f"No prompt found for step {step_num}")
            return None

        # Format context manually to avoid template issues with curly braces
        # Pass the step number to the format method
        formatted_context = self._format_context_for_prompt(context, step_num)

        # Create PromptTemplate with no input variables since we've pre-filled everything
        prompt = PromptTemplate(template=formatted_context, input_variables=[])

        # Create the chain with the LLM and prompt
        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            verbose=self.config.log_level == "DEBUG",
            memory=SimpleMemory(memories={"context": context}),
        )

        return chain

    def _format_context_for_prompt(self, context, step_num=None):
        """
        Format context dictionary into a readable string for prompt inclusion.
        Updated to use the LLM evaluation results.
        """
        # If step_num is not provided, use context information or default to step 1
        if step_num is None:
            step_num = 1

        # Create a base template with placeholders
        if step_num not in self.STEP_PROMPTS:
            self.logger.error(f"Invalid step number: {step_num}")
            return "Error: Invalid step number"

        template = self.STEP_PROMPTS[step_num]

        if step_num == 4:
            template = self.STEP_PROMPTS[step_num]

            # Basic repo information
            template = template.replace("${name}", context.get("name", "Unknown"))
            template = template.replace(
                "${language}", context.get("language", "Unknown")
            )

            # Framework information
            if context.get("is_spring_boot", False):
                template = template.replace(
                    "${is_spring_boot}", "This is a Spring Boot application."
                )
            else:
                template = template.replace("${is_spring_boot}", "")

            # Build system
            template = template.replace(
                "${build_system}", context.get("build_system", "unknown")
            )

            # README assessment
            template = template.replace(
                "${readme_recommendation}",
                context.get("readme_recommendation", "OVERWRITE"),
            )

            # Include the LLM's evaluation text
            evaluation = context.get(
                "readme_evaluation", "No detailed evaluation available."
            )
            # Limit the evaluation to a reasonable length
            if len(evaluation) > 1000:
                evaluation = evaluation[:997] + "..."
            template = template.replace("${readme_evaluation}", evaluation)

            # IMPORTANT: Replace README content placeholders
            template = template.replace(
                "${original_readme}",
                context.get("original_readme", "No original README found."),
            )
            template = template.replace(
                "${generated_readme}",
                context.get("generated_readme", "No generated README available."),
            )

            # Clean up any potential duplicate newlines
            template = re.sub(r"\n{3,}", "\n\n", template)

            return template

        # Basic repo information
        template = template.replace("${name}", context.get("name", "Unknown"))
        template = template.replace(
            "${language}", context.get("primary_language", "Unknown")
        )

        # Framework information
        if context.get("is_spring_boot", False):
            template = template.replace(
                "${is_spring_boot}", "This is a Spring Boot application."
            )
        else:
            template = template.replace("${is_spring_boot}", "")

        # Build system info
        template = template.replace(
            "${build_system}", f"Build System: {context.get('build_system', 'unknown')}"
        )

        # Analysis information - check for empty content
        formatted_analysis = context.get("formatted_analysis", "").strip()
        template = template.replace("${formatted_analysis}", formatted_analysis)

        # Entry points - CRITICAL for understanding how to run the application
        entry_points = context.get("entry_points", [])
        if entry_points:
            entry_points_str = "\n".join([f"- {ep}" for ep in entry_points])
            template = template.replace(
                "${entry_points}", f"## Entry Points\n{entry_points_str}"
            )
        else:
            template = template.replace("${entry_points}", "")

        # Key components/files
        key_components = context.get("key_project_files", [])
        if key_components:
            key_components_str = "\n".join([f"- {kc}" for kc in key_components])
            template = template.replace(
                "${key_components}", f"## Key Components\n{key_components_str}"
            )
        else:
            template = template.replace("${key_components}", "")

        # Key files content - skip if empty
        key_files_content = ""
        key_files = context.get("key_files_content", {})

        # First check if there's any non-empty content at all
        has_key_files_content = False
        for content in key_files.values():
            if content and content.strip():
                has_key_files_content = True
                break

        if has_key_files_content:
            # For Step 2, prioritize important files first
            if step_num == 2:
                # Process critical files first to ensure they appear at the top
                critical_files = [
                    "build.gradle",

                ]

                # First process critical files
                for critical_path in critical_files:
                    if critical_path in key_files:
                        content = key_files[critical_path]
                        if content and content.strip():
                            key_files_content += (
                                f"### {critical_path}\n```\n{content}\n```\n\n"
                            )

                # Then process entry point files
                for path in entry_points:
                    if path in key_files and path not in critical_files:
                        content = key_files[path]
                        if content and content.strip():
                            key_files_content += f"### {path}\n```\n{content}\n```\n\n"

                # Then process remaining files
                for path, content in key_files.items():
                    if path not in critical_files and path not in entry_points:
                        if content and content.strip():
                            key_files_content += f"### {path}\n```\n{content}\n```\n\n"
            else:
                for path, content in key_files.items():
                    if not content or content.strip() == "":
                        continue

                    key_files_content += f"### {path}\n```\n{content}\n```\n\n"

        template = template.replace("${key_files_content}", key_files_content)

        # Configuration files - skip if empty
        config_files_content = ""
        config_files = context.get("config_files", [])

        # First check if there's any non-empty content
        has_config_content = False
        for config in config_files:
            if isinstance(config, dict):
                content = config.get("content", "")
            else:
                content = context.get("file_contents", {}).get(config, "")

            if content and content.strip():
                has_config_content = True
                break

        if has_config_content:
            for config in config_files:
                if isinstance(config, dict):
                    path = config.get("path", "unknown")
                    content = config.get("content", "")
                else:
                    path = config
                    content = context.get("file_contents", {}).get(path, "")

                # Skip files with empty content
                if not content or content.strip() == "":
                    continue

                config_files_content += f"### {path}\n```\n{content}\n```\n\n"

        template = template.replace("${config_files}", config_files_content)

        # Shell scripts - only include non-empty lists
        shell_scripts = context.get("shell_scripts", [])
        if shell_scripts:
            shell_scripts_str = "\n".join([f"- {s}" for s in shell_scripts])
            template = template.replace(
                "${shell_scripts}", f"## Shell Scripts\n{shell_scripts_str}"
            )
        else:
            template = template.replace("${shell_scripts}", "")

        # Root shell scripts - only include non-empty lists
        root_scripts = context.get("root_shell_scripts", [])
        if root_scripts:
            root_scripts_str = "\n".join([f"- {s}" for s in root_scripts])
            template = template.replace(
                "${root_shell_scripts}", f"## Root Shell Scripts\n{root_scripts_str}"
            )
        else:
            template = template.replace("${root_shell_scripts}", "")
        # Run commands - check for empty objects at each level
        run_commands_content = ""
        has_commands = False

        if "run_commands" in context:
            run_commands = context.get("run_commands", {})

            # Check build commands
            build_cmds = run_commands.get("build", {})
            if build_cmds and any(cmds for cmds in build_cmds.values() if cmds):
                has_commands = True
                run_commands_content += "### Build Commands\n"
                for cmd_type, cmds in build_cmds.items():
                    if not cmds:  # Skip empty command lists
                        continue

                    if isinstance(cmds, list):
                        if not cmds:  # Skip empty lists
                            continue
                        for cmd in cmds:
                            run_commands_content += f"- {cmd_type}: `{cmd}`\n"
                    else:
                        run_commands_content += f"- {cmd_type}: `{cmds}`\n"
        if has_commands:
            template = template.replace("${run_commands}", run_commands_content)
        else:
            template = template.replace("${run_commands}", "")

        # Include previous step outputs for final README generation
        if "project_purpose" in context and context["project_purpose"].strip():
            template = template.replace(
                "${project_purpose}", context["project_purpose"].strip()
            )
        else:
            template = template.replace(
                "${project_purpose}", "No project purpose identified."
            )

        if "usage_instructions" in context and context["usage_instructions"].strip():
            template = template.replace(
                "${usage_instructions}", context["usage_instructions"].strip()
            )
        else:
            template = template.replace(
                "${usage_instructions}", "No usage instructions available."
            )

        # Clean up any potential duplicate newlines to keep the prompt clean
        template = re.sub(r"\n{3,}", "\n\n", template)

        return template

    def _get_step_name(self, step_num):
        """Get the name of a step from its file."""
        step_files = self.find_step_files()
        for file in step_files:
            if self.extract_step_number(file) == step_num:
                return file.stem[3:]  # Remove the "XX-" prefix
        return "unknown-step"

    def get_last_completed_step(self) -> int:
        """Find the last completed step by checking output files."""
        if not self.config.output_dir.exists():
            return 0

        pattern = re.compile(r"step_(\d+)_output\.md$")
        completed_steps = [
            int(m.group(1))
            for f in self.config.output_dir.iterdir()
            if (m := pattern.match(f.name)) and f.stat().st_size > 0
        ]

        last_step = max(completed_steps, default=0)
        self.logger.info(f"Last completed step: {last_step}")
        return last_step
