"""Configuration module for README generator."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GeneratorConfig:
    """Configuration for the README generator."""

    target_repo: str
    prompt_collection: str = "default"
    start_step: Optional[int] = None
    only_mode: bool = False
    model: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    keep_steps: bool = False
    language: str = "auto"  # Language analyzer to use: auto, java, python, javascript
    log_level: str = "DEBUG"
    save_intermediates: bool = False  # Flag to control saving intermediate debug files

    def __post_init__(self) -> None:
        """Initialize derived configuration values."""
        self.target_repo = Path(self.target_repo).resolve()

        self.script_dir = Path(__file__).parent.resolve()
        self.project_root = self.script_dir.parent
        self.prompts_dir = self.project_root / "prompts" / self.prompt_collection

        self.output_dir = self.target_repo / "output"

        self.intermediates_dir = self.output_dir / "intermediates"

        self.output_dir.mkdir(exist_ok=True, parents=True)
        if self.save_intermediates:
            self.intermediates_dir.mkdir(exist_ok=True, parents=True)

    def validate(self) -> None:
        """Validate all required directories exist."""
        if not self.target_repo.is_dir():
            raise ValueError(
                f"Target repository directory does not exist: {self.target_repo}"
            )

        # Find prompts in the '/prompts' repo
        if not self.prompts_dir.is_dir():
            repo_prompts = self.target_repo / "prompts" / self.prompt_collection
            if not repo_prompts.is_dir():
                prompts_parent = self.project_root / "prompts"
                if prompts_parent.is_dir():
                    available = [p.name for p in prompts_parent.iterdir() if p.is_dir()]
                    available_str = ", ".join(available) if available else "none found"
                else:
                    available_str = "none found (prompts directory missing)"

                raise ValueError(
                    f"Prompt collection '{self.prompt_collection}' not found. "
                    f"Available: {available_str}"
                )
            self.prompts_dir = repo_prompts

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True, parents=True)

        if self.save_intermediates:
            self.intermediates_dir.mkdir(exist_ok=True, parents=True)

        # Validate language choice
        if self.language not in ["auto", "java", "python", "javascript"]:
            raise ValueError(
                f"Invalid language choice: {self.language}. "
                f"Must be one of 'auto', 'java', 'python', or 'javascript'."
            )
