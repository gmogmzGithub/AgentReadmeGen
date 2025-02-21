"""Main README generator implementation with enhanced code understanding."""

import os
import logging
import re
from pathlib import Path
from typing import List

from analyzer import RepositoryAnalyzer
from config import GeneratorConfig

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from openai import OpenAI


class ReadmeGenerator:
    """Generates README documentation using AI-powered prompts with code understanding."""

    def __init__(self, config: GeneratorConfig) -> None:
        """Initialize the README generator.

        Args:
            config: Configuration object for the generator
        """
        self.config = config
        self.analyzer = RepositoryAnalyzer(self.config)
        self.llm = ChatOpenAI(model=config.model, temperature=0)
        self._has_checked_skipped = False

        # Enhanced prompt for technical audience
        self.context_prompt = PromptTemplate.from_template(
            """You are assisting in generating a README for a code repository. Your audience consists of 
            experienced engineers and developers who are familiar with standard development practices.

            # Previous Outputs
            {previous_context}

            # Repository Analysis
            {repo_analysis}

            # Code Understanding
            {code_understanding}

            # Current Task
            {current_prompt}

            Focus on generating content that will be useful for experienced engineers and developers.
            Base your answers on the actual code functionality and architecture, not basic usage.
            Include only ./gradlew and hoboRon commands where applicable, omit other basic instructions.
            """
        )

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

        return valid_files

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

        return max(completed_steps, default=0)

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

        # Return combined outputs
        return "\n\n".join(outputs)

    def process_prompt(self, prompt_file: Path) -> bool:
        """Process a single prompt file using LangChain PromptTemplate.

        Args:
            prompt_file: Path to the prompt file

        Returns:
            True if processing succeeded, False otherwise
        """
        step_num = self.extract_step_number(prompt_file)
        if step_num == 0:
            logging.error(f"Invalid step number in prompt: {prompt_file}")
            return False

        output_file = self.get_output_path(step_num)

        logging.info(f"Processing prompt: {prompt_file.name} (Step {step_num})")

        # Get content from previous steps
        previous_context = self.prepare_context(step_num)

        # Get content of the prompt file
        prompt_content = prompt_file.read_text()

        # Get repository analysis
        repo_analysis = self.analyzer.analyze_repository(update=False)

        # Extract code understanding from repository analysis
        code_understanding = self.analyzer.repo_info.get(
            "code_understanding", "No code understanding analysis available."
        )

        try:
            # Format the prompt with enhanced code understanding
            formatted_prompt = self.context_prompt.format(
                previous_context=previous_context,
                repo_analysis=repo_analysis,
                code_understanding=code_understanding,
                current_prompt=prompt_content,
            )

            # Generate response using LLM
            response = self.llm.invoke(formatted_prompt)
            # Make sure we extract the content from the AIMessage
            response_content = response.content

            # Write to output file
            output_file.write_text(response_content)

            logging.info(f"Successfully processed step {step_num}")
            return True

        except Exception as e:
            logging.error(f"Error processing step {step_num}: {e}")
            return False

    def finalize_readme(self) -> None:
        """Create the final README file that properly preserves content from individual steps."""
        # Find all existing output files
        existing_outputs = list(self.config.output_dir.glob("step_*_output.md"))
        if not existing_outputs:
            raise FileNotFoundError("No output files found to create README from")

        # Sort by step number
        existing_outputs.sort(key=lambda p: int(p.stem.split("_")[1]))

        # Read content from all files
        step_outputs = []
        for output_file in existing_outputs:
            try:
                step_num = int(output_file.stem.split("_")[1])
                content = output_file.read_text()
                step_outputs.append(
                    {"step": step_num, "file": output_file.name, "content": content}
                )
                logging.info(f"Included content from: {output_file}")
            except Exception as e:
                logging.warning(f"Could not read {output_file}: {e}")

        if not step_outputs:
            raise FileNotFoundError("No valid content found in output files")

        try:
            # Create a more focused prompt for technical audience
            final_prompt = PromptTemplate.from_template(
                """You are compiling a technical README.md for a software project. Your audience consists of 
                experienced engineers and developers who are familiar with standard development practices 
                and internal company libraries.

                # Key Instructions:
                1. Focus on WHAT the repository does and WHY it exists
                2. Highlight technical architecture and design decisions
                3. Document only non-obvious configuration or setup requirements
                4. Assume the audience knows:
                   - Basic development tools and practices
                   - How to use git, gradle, maven, npm etc.
                   - Standard CI/CD processes
                5. Use clear, concise technical language
                6. Remove any obvious or basic instructions, with these exceptions:
                   - Include './gradlew build' and './gradlew clean build' if it's a Gradle project
                   - Include 'hoboRon' commands if Hobo deployment is configured
                   - Remove all other basic git/gradle/maven/npm commands
                7. DO NOT include notes about AI generation
                8. DO NOT include generic summaries at the end

                # Code Understanding:
                {code_understanding}

                # Sections to Compile:
                {sections}

                Produce a streamlined, technical README.md that explains what this repository is for 
                and how it works. Focus on architecture, design decisions, and non-obvious technical details.
                """
            )

            # Get code understanding from repository analysis
            code_understanding = self.analyzer.repo_info.get(
                "code_understanding", "No code understanding analysis available."
            )

            # Format the sections with clear separation
            formatted_sections = "\n\n".join(
                [
                    f"## Section {s['step']}: {s['file']}\n{s['content']}"
                    for s in step_outputs
                ]
            )

            # Generate final README with emphasis on technical content
            response = self.llm.invoke(
                final_prompt.format(
                    code_understanding=code_understanding, sections=formatted_sections
                )
            )
            readme_content = response.content

            # Remove any ```markdown or ``` tags that might be in the response
            readme_content = re.sub(r"^```markdown\s*", "", readme_content)
            readme_content = re.sub(r"\s*```$", "", readme_content)

            lines = readme_content.split("\n")
            title_index = next(
                (i for i, line in enumerate(lines) if line.startswith("# ")), 0
            )

            disclosure = "\n> **Note:** This README was automatically generated using AI. While we've made every effort to ensure its accuracy, there may be mistakes or omissions. Please verify critical information before use."

            if title_index < len(lines) - 1:
                lines.insert(
                    title_index + 1, disclosure
                )  # +1 to place right after title
            else:
                lines.insert(0, disclosure)

            readme_content = "\n".join(lines)

            # Create the combined README
            target_readme = self.config.target_repo / "ai.README.md"
            target_readme.write_text(readme_content)

            logging.info(f"\nREADME generation complete: {target_readme}")
            logging.info(f"Combined {len(step_outputs)} section files")

        except Exception as e:
            logging.error(f"Failed to write combined README: {e}")
            raise FileNotFoundError(f"Failed to write combined README: {e}")

    def cleanup_step_files(self) -> None:
        """Remove all intermediate step output files after final README generation."""
        try:
            step_files = list(self.config.output_dir.glob("step_*_output.md"))
            if not step_files:
                logging.info("No step files to clean up")
                return

            # Remove each file
            for file in step_files:
                try:
                    file.unlink()
                    logging.info(f"Removed intermediate file: {file}")
                except Exception as e:
                    logging.warning(f"Failed to remove {file}: {e}")

            logging.info(
                f"Successfully cleaned up {len(step_files)} intermediate files"
            )

        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    # In readme_generator.py, update the run() method:

    def run(self) -> None:
        """Main execution flow."""
        try:
            self.config.validate()

            # Change to target repo directory
            os.chdir(self.config.target_repo)

            # First... run the analyzer to check for existing README
            analysis_result = self.analyzer.analyze_repository()

            # Check if we should skip processing due to existing README
            if (
                isinstance(analysis_result, str)
                and "Non-empty README already exists" in analysis_result
            ):
                logging.info(analysis_result)
                return

            # Find all valid step files
            step_files = self.find_step_files()
            if not step_files:
                logging.error("No valid step files found")
                return

            # Determine step range
            if self.config.only_mode:
                if self.config.start_step is None:
                    raise ValueError("--only must be used with --step")
                final_step = self.config.start_step
                start_step = self.config.start_step
            else:
                if self.config.start_step is None:
                    last_completed = self.get_last_completed_step()
                    start_step = last_completed + 1 if last_completed > 0 else 1
                else:
                    start_step = self.config.start_step
                final_step = max(self.extract_step_number(f) for f in step_files)

            # Process steps
            processed_any = False
            failed_steps = []

            for prompt_file in step_files:
                current_step = self.extract_step_number(prompt_file)
                if current_step < start_step:
                    continue
                if current_step > final_step:
                    break

                if not self.process_prompt(prompt_file):
                    logging.warning(f"Failed to process step {current_step}")
                    failed_steps.append(current_step)
                else:
                    processed_any = True

            # Finalize README if any steps were processed successfully
            if not self.config.only_mode and processed_any:
                self.finalize_readme()

                # Only clean up if keep_steps flag is False
                if not self.config.keep_steps:
                    self.cleanup_step_files()
                    logging.info("Intermediate step files have been cleaned up")
                else:
                    logging.info("Keeping intermediate step files as requested")

            # Log results
            if failed_steps:
                logging.warning(f"The following steps failed: {failed_steps}")

        except Exception as e:
            logging.error(f"Error during execution: {e}")
            raise
