"""Utilities for debugging and saving intermediate files during README generation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("debug_utils")


class IntermediateFileManager:
    """Manages saving intermediate files during README generation for debugging purposes."""

    def __init__(self, config):
        """Initialize the intermediate file manager.

        Args:
            config: Generator configuration with save_intermediates flag and directories
        """
        self.config = config
        self.enabled = config.save_intermediates

        # We'll always use the output directory
        self.output_dir = config.output_dir

        # If intermediates saving is enabled, use the intermediates subdirectory
        if self.enabled:
            self.intermediates_dir = config.intermediates_dir
            self.intermediates_dir.mkdir(exist_ok=True, parents=True)
            logger.info(
                f"Intermediate file saving enabled to: {self.intermediates_dir}"
            )
        else:
            logger.debug("Intermediate file saving disabled")

    def save_context(
        self,
        repo_name: str,
        step_num: int,
        step_name: str,
        context: Dict[Any, Any],
        model_identifier: str,
    ) -> Optional[Path]:
        """Save enhanced context for a generation step to a JSON file.

        Args:
            repo_name: Repository name
            step_num: Current processing step number
            step_name: Name of the current step
            context: Enhanced context dictionary
            model_identifier: Identifier for the model being used

        Returns:
            Path to the saved file or None if saving is disabled
        """
        if not self.enabled:
            return None

        try:
            # Create filename
            context_filename = f"{repo_name}_step{step_num}_{step_name}_context_{model_identifier}.json"
            context_path = self.intermediates_dir / context_filename

            # Convert context to JSON serializable format
            json_context = {}
            for key, value in context.items():
                # Handle non-serializable types
                if (
                    isinstance(value, (str, int, float, bool, list, dict))
                    or value is None
                ):
                    json_context[key] = value
                else:
                    json_context[key] = str(value)

            # Write to file
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(json_context, f, indent=2, default=str)

            logger.info(f"Enhanced context saved to: {context_path}")
            return context_path

        except Exception as e:
            logger.error(f"Error saving context file: {str(e)}")
            return None

    def save_prompt(
        self,
        repo_name: str,
        step_num: int,
        step_name: str,
        prompt: str,
        model_identifier: str,
    ) -> Optional[Path]:
        """Save the full prompt for a generation step.

        Args:
            repo_name: Repository name
            step_num: Current processing step number
            step_name: Name of the current step
            prompt: Full prompt text
            model_identifier: Identifier for the model being used

        Returns:
            Path to the saved file or None if saving is disabled
        """
        if not self.enabled:
            return None

        try:
            # Create filename
            prompt_filename = (
                f"{repo_name}_step{step_num}_{step_name}_prompt_{model_identifier}.log"
            )
            prompt_path = self.intermediates_dir / prompt_filename

            # Write to file
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)

            logger.info(f"Full prompt saved to: {prompt_path}")
            return prompt_path

        except Exception as e:
            logger.error(f"Error saving prompt file: {str(e)}")
            return None

    def save_step_output(
        self,
        repo_name: str,
        step_num: int,
        step_name: str,
        output: str,
        model_identifier: str,
    ) -> Optional[Path]:
        """Save the output from a generation step.

        Args:
            repo_name: Repository name
            step_num: Current processing step number
            step_name: Name of the current step
            output: Generation step output text
            model_identifier: Identifier for the model being used

        Returns:
            Path to the saved file or None if saving is disabled
        """
        if not self.enabled:
            return None

        try:
            # Create filename
            output_filename = f"step_{step_num:02d}_{step_name}_output_{repo_name}_{model_identifier}.md"
            output_path = self.intermediates_dir / output_filename

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)

            logger.info(f"Step output saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving step output file: {str(e)}")
            return None

    def save_repo_context(
        self, repo_context: Dict[Any, Any], model_identifier: str
    ) -> Optional[Path]:
        """Save the repository context information as a JSON file.

        Args:
            repo_context: Repository analysis context
            model_identifier: Identifier for the model being used

        Returns:
            Path to the saved file or None if saving is disabled
        """
        if not self.enabled:
            return None

        try:
            repo_name = repo_context.get("name", "unknown_repo")
            filename = f"{repo_name}_repo_context_{model_identifier}.json"
            json_path = self.intermediates_dir / filename

            # Clean the context to remove large file contents
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

            # Write to file
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(clean_context, f, indent=2, default=str)

            logger.info(f"Repository context saved to: {json_path}")
            return json_path

        except Exception as e:
            logger.error(f"Error saving repository context JSON: {str(e)}")
            return None

    def save_final_readme(
        self, repo_name: str, readme_content: str, model_identifier: str
    ) -> Optional[Path]:
        """Save the final README to the output directory.

        Args:
            repo_name: Repository name
            readme_content: Final README content
            model_identifier: Identifier for the model being used

        Returns:
            Path to the saved file
        """
        try:
            readme_with_watermark = add_watermark(readme_content, model_identifier)

            # Save the final README to the output directory, regardless of intermediates flag
            readme_filename = f"README.md"
            readme_path = self.config.target_repo / readme_filename

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_with_watermark)

            logger.info(f"Final README saved to: {readme_path}")

            if self.enabled:
                intermediates_readme_path = (
                    self.intermediates_dir / f"{repo_name}_ai.README.md"
                )
                with open(intermediates_readme_path, "w", encoding="utf-8") as f:
                    f.write(readme_with_watermark)
                logger.info(
                    f"Copy of final README saved to: {intermediates_readme_path}"
                )

                reasoning_path = self.config.output_dir / "reasoning.md"
                if reasoning_path.exists():
                    intermediates_reasoning_path = (
                        self.intermediates_dir / f"{repo_name}_reasoning.md"
                    )
                    reasoning_content = reasoning_path.read_text(encoding="utf-8")
                    with open(intermediates_reasoning_path, "w", encoding="utf-8") as f:
                        f.write(reasoning_content)
                    logger.info(f"Reasoning saved to: {intermediates_reasoning_path}")

                    # Delete the reasoning.md file if keep_steps is not set
                    if not self.config.keep_steps:
                        reasoning_path.unlink()
                        logger.info(f"Deleted reasoning file: {reasoning_path}")

            return readme_path

        except Exception as e:
            logger.error(f"Error saving final README: {str(e)}")
            return None


def add_watermark(readme_content, model_identifier):
    """Add a discreet watermark to the README content.

    Args:
        readme_content: The README content to append the watermark to
        model_identifier: Identifier for the model used for generation

    Returns:
        README content with watermark appended
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Format a professional, discreet watermark
    watermark = f"\n\n###### AI Generated README\nGenerated on {timestamp} | Model: {model_identifier}"

    return readme_content + watermark
