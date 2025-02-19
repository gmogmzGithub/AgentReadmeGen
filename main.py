#!/usr/bin/env python3

"""Command-line interface for the README generator."""

import argparse
import logging
import sys

from readme_generator import ReadmeGenerator
from config import GeneratorConfig


def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )


def main():
    """Main entry point for the README generator."""
    parser = argparse.ArgumentParser(
        description="Generate README from prompts using AI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-r", "--repo", required=True, help="Target repository directory")
    parser.add_argument("-c", "--collection", default="default", help="Prompt collection to use")
    parser.add_argument("-s", "--step", type=int, help="Step number to start from")
    parser.add_argument("-o", "--only", action="store_true", help="Run only specific step")
    parser.add_argument("-m", "--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--keep-steps", action="store_true", help="Keep intermediate step output files after generation")

    args = parser.parse_args()
    setup_logging()

    try:
        config = GeneratorConfig(
            target_repo=args.repo,
            prompt_collection=args.collection,
            start_step=args.step,
            only_mode=args.only,
            model=args.model
        )

        generator = ReadmeGenerator(config)
        generator.run()

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()