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
    model: str = "gpt-4o"
    keep_steps: bool = False  # Add this parameter with a default value of False

    def __post_init__(self) -> None:
        """Initialize derived configuration values."""
        self.target_repo = Path(self.target_repo).resolve()

        self.script_dir = Path(__file__).parent.resolve()
        self.prompts_dir = self.script_dir / "prompts" / self.prompt_collection
        self.output_dir = self.target_repo / "output"

    def validate(self) -> None:
        """Validate all required directories exist."""
        if not self.target_repo.is_dir():
            raise ValueError(
                f"Target repository directory does not exist: {self.target_repo}"
            )

        if not self.prompts_dir.is_dir():
            # Find prompts in the '/prompts' repo
            repo_prompts = self.target_repo / "prompts" / self.prompt_collection
            if not repo_prompts.is_dir():
                available = [
                    p.name
                    for p in (self.script_dir / "prompts").iterdir()
                    if p.is_dir()
                ]
                raise ValueError(
                    f"Prompt collection '{self.prompt_collection}' not found. "
                    f"Available: {', '.join(available)}"
                )
            self.prompts_dir = repo_prompts

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True, parents=True)
