"""Utility functions for file operations and analysis."""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple


def read_file_content(
    file_path: Path, max_size: int = 102400, encoding: str = "utf-8"
) -> Optional[str]:
    """Read content from a file with error handling and size limit.

    Args:
        file_path: Path to the file
        max_size: Maximum file size in bytes
        encoding: File encoding

    Returns:
        File content as string or None if file can't be read
    """
    try:
        if not file_path.exists() or not file_path.is_file():
            return None

        file_stat = os.stat(file_path)
        if file_stat.st_size > max_size:
            return None

        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None


def find_files_by_extensions(
    directory: Path, extensions: Set[str], exclude_dirs: Set[str] = None
) -> List[Path]:
    """Find all files with specified extensions in a directory.

    Args:
        directory: Root directory to search
        extensions: Set of file extensions to include
        exclude_dirs: Set of directory names to exclude from search

    Returns:
        List of paths to matching files
    """
    if exclude_dirs is None:
        exclude_dirs = {
            ".git",
            "node_modules",
            "venv",
            "__pycache__",
            "target",
            "build",
            "dist",
            ".gradle",
            "lemma",  # Temporarily ignore 'lemma' directory - will be needed in future
        }

    result = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = Path(os.path.join(root, file))
            if any(file_path.name.endswith(ext) for ext in extensions):
                result.append(file_path)

    return result


def find_files_by_pattern(
    directory: Path, pattern: str, exclude_dirs: Set[str] = None
) -> List[Path]:
    """Find all files matching a pattern in a directory.

    Args:
        directory: Root directory to search
        pattern: Pattern to match in filename
        exclude_dirs: Set of directory names to exclude from search

    Returns:
        List of paths to matching files
    """
    if exclude_dirs is None:
        exclude_dirs = {
            ".git",
            "node_modules",
            "venv",
            "__pycache__",
            "target",
            "build",
            "dist",
            ".gradle",
            "lemma",  # Temporarily ignore 'lemma' directory - will be needed in future
        }

    result = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if pattern in file:
                result.append(Path(os.path.join(root, file)))

    return result


def get_file_info(
    file_path: Path, repo_root: Path, max_size: int = 102400
) -> Dict[str, Any]:
    """Create a dictionary with information about a file.

    Args:
        file_path: Path to the file
        repo_root: Root directory of the repository
        max_size: Maximum file size to read content

    Returns:
        Dictionary with file information
    """
    rel_path = file_path.relative_to(repo_root)

    try:
        file_stat = os.stat(file_path)

        file_info = {
            "path": str(rel_path),
            "size": file_stat.st_size,
            "is_key_file": False,
            "is_entry_point": False,
            "is_config": False,
            "language": "Unknown",
        }

        # Add content if file size is under the limit
        if file_stat.st_size <= max_size:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                file_info["content"] = f.read()

        return file_info

    except Exception as e:
        print(f"Error getting info for {file_path}: {str(e)}")
        return {
            "path": str(rel_path),
            "error": str(e),
        }


def extract_patterns_from_file(
    file_path: Path, patterns: Dict[str, str]
) -> Dict[str, List[str]]:
    """Extract patterns from a file using regular expressions.

    Args:
        file_path: Path to the file
        patterns: Dictionary of pattern names to regex patterns

    Returns:
        Dictionary of pattern names to lists of matches
    """
    content = read_file_content(file_path)
    if not content:
        return {name: [] for name in patterns}

    results = {}
    for name, pattern in patterns.items():
        results[name] = re.findall(pattern, content, re.DOTALL)

    return results


def check_file_contains(
    file_path: Path, patterns: List[str], case_sensitive: bool = True
) -> List[str]:
    """Check if a file contains any of the specified patterns.

    Args:
        file_path: Path to the file
        patterns: List of string patterns to search for
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        List of patterns that were found in the file
    """
    content = read_file_content(file_path)
    if not content:
        return []

    if not case_sensitive:
        content = content.lower()
        patterns = [p.lower() for p in patterns]

    return [p for p in patterns if p in content]


def is_config_file(file_path: Path) -> bool:
    """Determine if a file is likely a configuration file.

    Args:
        file_path: Path to the file

    Returns:
        Boolean indicating if the file is a configuration file
    """
    # Common config file extensions
    config_extensions = {".yml", ".yaml", ".properties"}

    # Common config file patterns
    config_patterns = {"config", "settings", "properties", "application"}

    path_str = str(file_path).lower()

    # Check by extension
    if any(path_str.endswith(ext) for ext in config_extensions):
        return True

    # Check by name patterns
    return any(pattern in path_str for pattern in config_patterns)
