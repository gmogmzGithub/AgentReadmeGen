#!/usr/bin/env python3

"""Command-line interface for the README generator."""

import argparse
import logging
import sys
from dotenv import load_dotenv

from src.analyzers import get_analyzer_for_repo
from src.readme_generator import ReadmeGenerator
from src.config import GeneratorConfig


def setup_logging(config):
    """Set up basic logging configuration.

    Args:
        config: Generator configuration with log_level
    """
    level_str = config.log_level.upper()
    level = getattr(logging, level_str, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    """Main entry point for the README generator."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate README from repository analysis using AI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-r", "--repo", required=True, help="Target repository directory"
    )
    parser.add_argument(
        "-c", "--collection", default="default", help="Prompt collection to use"
    )
    parser.add_argument("-s", "--step", type=int, help="Step number to start from")
    parser.add_argument(
        "-o", "--only", action="store_true", help="Run only specific step"
    )
    parser.add_argument(
        "-m",
        "--model",
        default="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        choices=["us.anthropic.claude-3-5-sonnet-20241022-v2:0", "gpt-4o"],
        help="Model to use (Claude or OpenAI)",
    )
    parser.add_argument(
        "--keep-steps",
        action="store_true",
        help="Keep intermediate step output files after generation",
    )
    parser.add_argument(
        "--language",
        choices=["auto", "java", "python", "javascript"],
        default="auto",
        help="Force specific language analyzer instead of auto-detection",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="DEBUG",
        help="Set the logging level",
    )
    parser.add_argument(
        "--save-intermediates",
        action="store_true",
        help="Save intermediate files and debug information to 'output/intermediates' directory",
    )

    args = parser.parse_args()

    try:
        config = GeneratorConfig(
            target_repo=args.repo,
            prompt_collection=args.collection,
            start_step=args.step,
            only_mode=args.only,
            model=args.model,
            keep_steps=args.keep_steps,
            language=args.language,
            log_level=args.log_level,
            save_intermediates=args.save_intermediates,
        )

        setup_logging(config)
        logging.info(f"Using model: {config.model}")

        if config.save_intermediates:
            logging.info(f"Saving intermediate files to: {config.intermediates_dir}")

        # Get the appropriate analyzer for the repository
        analyzer = get_analyzer_for_repo(config)

        # Create and run the README generator
        generator = ReadmeGenerator(config, analyzer)
        generator.run()

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
