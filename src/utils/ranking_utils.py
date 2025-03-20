"""Utility functions for ranking files by importance."""

from pathlib import Path
from typing import Dict, Any, List, Callable


def rank_by_criteria(file_info: Dict[str, Any], criteria: Dict[str, int]) -> int:
    """Rank a file's importance based on specified criteria.

    Args:
        file_info: Dictionary with file information
        criteria: Dictionary mapping criteria names to score values

    Returns:
        Integer score representing file importance
    """
    score = 0
    path = file_info.get("path", "").lower()

    # Apply path-based criteria
    for pattern, value in criteria.items():
        if pattern in path:
            score += value

    return score


def rank_by_type(file_info: Dict[str, Any], type_scores: Dict[str, int]) -> int:
    """Rank a file based on its type/extension.

    Args:
        file_info: Dictionary with file information
        type_scores: Dictionary mapping file extensions to score values

    Returns:
        Integer score based on file type
    """
    score = 0
    path = file_info.get("path", "").lower()

    for ext, value in type_scores.items():
        if path.endswith(ext):
            score += value
            break

    return score


def rank_by_content_patterns(
    file_info: Dict[str, Any], patterns: Dict[str, Dict[str, int]]
) -> int:
    """Rank a file based on patterns found in its content.

    Args:
        file_info: Dictionary with file information
        patterns: Dictionary mapping file extensions to dictionaries of
                 regex patterns and their score values

    Returns:
        Integer score based on content patterns
    """
    import re

    score = 0
    path = file_info.get("path", "").lower()
    content = file_info.get("content", "")

    if not content:
        return 0

    # Find applicable pattern set based on file extension
    for ext, pattern_set in patterns.items():
        if path.endswith(ext):
            # Apply each pattern in the set
            for pattern, value in pattern_set.items():
                matches = re.findall(pattern, content)
                score += len(matches) * value
            break

    return score


def apply_ranking_functions(
    file_info: Dict[str, Any], ranking_funcs: List[Callable]
) -> int:
    """Apply multiple ranking functions to a file.

    Args:
        file_info: Dictionary with file information
        ranking_funcs: List of ranking functions that take file_info and return a score

    Returns:
        Total score from all ranking functions
    """
    score = 0

    for func in ranking_funcs:
        score += func(file_info)

    return score


def sort_files_by_importance(
    files_info: List[Dict[str, Any]], ranking_func: Callable
) -> List[Dict[str, Any]]:
    """Sort a list of file info dictionaries by importance.

    Args:
        files_info: List of file information dictionaries
        ranking_func: Function that takes file_info and returns a score

    Returns:
        Sorted list of file information dictionaries
    """
    # First, score each file
    for file_info in files_info:
        file_info["importance_score"] = ranking_func(file_info)

    # Then sort by score (highest first)
    return sorted(files_info, key=lambda x: x.get("importance_score", 0), reverse=True)


def get_top_files_by_category(
    files_info: List[Dict[str, Any]],
    categories: Dict[str, Callable],
    max_per_category: int = 3,
    max_total: int = 25,
) -> List[Dict[str, Any]]:
    """Get top files across multiple categories.

    Args:
        files_info: List of file information dictionaries
        categories: Dictionary mapping category names to filter functions
        max_per_category: Maximum files to include per category
        max_total: Maximum total files to include

    Returns:
        List of top files across all categories
    """
    result = []
    added_paths = set()

    # Process each category
    for category, filter_func in categories.items():
        matching_files = [f for f in files_info if filter_func(f)]

        # Sort by importance score
        matching_files.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

        # Take top files from this category that aren't already included
        count = 0
        for file in matching_files:
            if file["path"] not in added_paths and count < max_per_category:
                result.append(file)
                added_paths.add(file["path"])
                count += 1

                if len(result) >= max_total:
                    return result

    # If we still have room, add any remaining files by importance score
    if len(result) < max_total:
        # Sort all files by importance score
        remaining = [f for f in files_info if f["path"] not in added_paths]
        remaining.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

        # Add until we reach the max
        for file in remaining:
            result.append(file)
            if len(result) >= max_total:
                break

    return result
