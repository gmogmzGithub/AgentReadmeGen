"""Utilities for README generation and processing."""

import re


def extract_reasoning(content):
    """Extract HTML comments (reasoning) from the README content.

    Args:
        content: The README content with HTML comments

    Returns:
        tuple: (readme_without_reasoning, reasoning_text)
    """
    # Pattern to match HTML comments
    pattern = r"<!--\s*(.*?)\s*-->"

    matches = re.findall(pattern, content, re.DOTALL)

    if not matches:
        return content, ""

    reasoning_text = "\n\n".join(matches)

    readme_without_reasoning = re.sub(pattern, "", content, flags=re.DOTALL)

    readme_without_reasoning = re.sub(r"\n{3,}", "\n\n", readme_without_reasoning)

    return readme_without_reasoning.strip(), reasoning_text.strip()
