"""Enhanced repository analysis module focusing on Java and Gradle codebases."""

import logging
import re
from typing import Dict, Any


class CodeUnderstandingAnalyzer:
    """Advanced code analysis focusing on purpose and functionality rather than structure."""

    def __init__(self, llm, max_tokens=32768):
        """Initialize the enhanced code understanding analyzer.

        Args:
            llm: Language model for analysis
            max_tokens: Maximum tokens to include in LLM context
        """
        self.llm = llm
        self.max_tokens = max_tokens
        self.logger = logging.getLogger("CodeUnderstandingAnalyzer")

    def _rank_file_importance(self, file_info: Dict[str, Any]) -> int:
        """Rank a file's importance for understanding functionality (higher is more important)."""
        score = 0
        path = file_info.get("path", "").lower()
        is_entry = file_info.get("is_entry_point", False)
        is_key = file_info.get("is_key_file", False)
        content = file_info.get("content", "")

        # Entry points are highest priority
        if is_entry:
            score += 100

        # Spring Boot application classes are crucial
        if content and re.search(r"@SpringBootApplication", content):
            score += 110

        # Key project files are high priority
        if is_key:
            score += 80

        if "application" in path:
            score += 70
            # Give higher priority to example configuration files
            if path.endswith((".example", ".template")):
                score += 100  # Additional points for example config files
        elif "main" in path:
            score += 65
        elif "controller" in path:
            score += 60
        elif "service" in path:
            score += 55
        elif "repository" in path or "dao" in path:
            score += 50
        elif "model" in path or "entity" in path:
            score += 45
        elif "config" in path:
            score += 40
        elif "util" in path or "helper" in path:
            score += 20

        if path.endswith(".gradle") or "gradle" in path:
            score += 75

        if path.endswith(".properties") or path.endswith(".yml"):
            if "application" in path:
                score += 70
                if "local" in path or "dev" in path:
                    score += 10
                # Set higher priority for example files that show required configuration
                if path.endswith((".example", ".template")):
                    score += 100

        # Check content for key indicators (if content is available)
        if content:
            # For Java files
            if path.endswith(".java"):
                spring_annotations = re.findall(
                    r"@(Controller|RestController|Service|Repository|Component|Configuration|SpringBootApplication)",
                    content,
                )
                score += len(spring_annotations) * 10

                if re.search(r"public\s+static\s+void\s+main", content):
                    score += 30

                rest_endpoints = re.findall(
                    r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)",
                    content,
                )
                score += len(rest_endpoints) * 8

            elif path.endswith(".gradle"):
                if re.search(r"org\.springframework\.boot", content):
                    score += 25

                if re.search(r"application|java", content):
                    score += 20

                # Custom tasks are important
                custom_tasks = re.findall(r"task\s+(\w+)", content)
                score += len(custom_tasks) * 5

        return score
