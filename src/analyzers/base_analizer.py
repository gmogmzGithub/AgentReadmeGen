"""Base repository analysis module."""

import os
import logging
from typing import Dict, List, Any
from src.utils import CustomChatOpenAI


class BaseAnalyzer:
    """Base class for repository analyzers with common functionality."""

    # Common project files to always include regardless of extension
    KEY_PROJECT_FILES = {
        "README.md",
        "Dockerfile",
        "docker-compose.yml",
    }

    # Maximum file size to analyze
    MAX_FILE_SIZE = 1024 * 100  # 100KB

    def __init__(self, config) -> None:
        """Initialize the base repository analyzer.

        Args:
            config: Generator configuration
        """
        self.config = config
        self.llm = CustomChatOpenAI(model=config.model, temperature=0)
        self.repo_info = {}
        self.analyzed = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_analyzable_extensions(self) -> set:
        """Get file extensions that should be analyzed.

        Should be overridden by subclasses.

        Returns:
            Set of file extensions to analyze.
        """
        return set()

    def _get_language_specific_key_files(self) -> set:
        """Get language-specific key files to always include.

        Should be overridden by subclasses.

        Returns:
            Set of key filenames to always include.
        """
        return set()

    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language based on file extension.

        Should be overridden by subclasses.

        Args:
            file_path: Path to the file

        Returns:
            String representing the detected language
        """
        return "Unknown"

    def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
        """Determine if a file is an entry point based on content and language.

        Should be overridden by subclasses.

        Args:
            content: File content
            language: Detected language
            file_path: Path to the file

        Returns:
            Boolean indicating if the file is an entry point
        """
        return False

    def _rank_file_importance(self, file_info: Dict[str, Any]) -> int:
        """Rank a file's importance based on language-specific criteria.

        Should be overridden by subclasses.

        Args:
            file_info: Dictionary with file information

        Returns:
            Integer score representing file importance
        """
        score = 0

        # Common scoring for all languages
        is_entry = file_info.get("is_entry_point", False)
        is_key = file_info.get("is_key_file", False)

        # Entry points are highest priority
        if is_entry:
            score += 100

        # Key project files are high priority
        if is_key:
            score += 80

        return score

    def _gather_file_info(self) -> Dict[str, Any]:
        """Gather information about files in the repository.

        Returns:
            Dictionary with file information
        """
        files_info = []
        entry_points = []
        config_files = []
        shell_scripts = []
        root_shell_scripts = []
        hobo_shell_scripts = []

        for root, _, files in os.walk(self.config.target_repo):
            # Skip common directories to ignore
            if any(
                part in root
                for part in [
                    ".git",
                    "node_modules",
                    "venv",
                    "__pycache__",
                    "target",
                    "build",
                    "dist",
                    ".gradle",
                    "lemma",  # TODO - Temporarily ignore 'lemma' directory - will be needed in future
                ]
            ):
                continue

            for file in files:
                if file.endswith(".sh"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.config.target_repo)

                    # Determine if this is a root script or hobo script
                    if os.sep in rel_path:
                        if rel_path.startswith("hobo" + os.sep):
                            hobo_shell_scripts.append(rel_path)
                    else:
                        root_shell_scripts.append(rel_path)

        # Get analyzable extensions and key files from concrete implementation
        analyzable_extensions = self._get_analyzable_extensions()
        key_project_files = self.KEY_PROJECT_FILES.union(
            self._get_language_specific_key_files()
        )

        # Track file stats for language detection
        language_stats = {}
        has_spring_boot = False

        # First pass to identify key project files regardless of extension
        for file_name in key_project_files:
            # Skip .gitlab-ci.yml file and Sonar-related files
            if file_name == ".gitlab-ci.yml" or self._is_sonar_file(file_name):
                continue

            file_path = self.config.target_repo / file_name
            if file_path.exists() and file_path.is_file():
                try:
                    rel_path = os.path.relpath(file_path, self.config.target_repo)
                    file_stat = os.stat(file_path)
                    if file_stat.st_size <= self.MAX_FILE_SIZE:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                        language = self._detect_language(rel_path)
                        is_config = self._is_config_file(rel_path)

                        # Check for Spring Boot Application
                        if language == "Java" and "@SpringBootApplication" in content:
                            has_spring_boot = True

                        # Track language stats
                        language_stats[language] = language_stats.get(language, 0) + 1

                        file_info = {
                            "path": rel_path,
                            "language": language,
                            "is_entry_point": False,  # Key project files usually aren't entry points
                            "is_config": is_config,
                            "size": file_stat.st_size,
                            "is_key_file": True,
                            "content": content,
                        }

                        files_info.append(file_info)

                        if is_config:
                            config_files.append(rel_path)
                            self.logger.debug(f"Added key config file: {rel_path}")

                        if rel_path.endswith(".sh"):
                            shell_scripts.append(rel_path)
                            # Ensure shell scripts are added to config_files
                            if rel_path not in config_files:
                                config_files.append(rel_path)
                                self.logger.debug(
                                    f"Added shell script to config files: {rel_path}"
                                )

                except Exception as e:
                    self.logger.warning(
                        f"Error processing key file {file_path}: {str(e)}"
                    )

        # Second pass for regular file discovery
        for root, _, files in os.walk(self.config.target_repo):
            # Skip common directories to ignore
            if any(
                part in root
                for part in [
                    ".git",
                    "node_modules",
                    "venv",
                    "__pycache__",
                    "target",
                    "build",
                    "dist",
                    ".gradle",
                    "lemma",  # TODO - Temporarily ignore 'lemma' directory - will be needed in future
                ]
            ):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.config.target_repo)

                # Skip .gitlab-ci.yml file and Sonar-related files
                if rel_path == ".gitlab-ci.yml" or self._is_sonar_file(rel_path):
                    continue

                # Skip if we already processed this file as a key file
                if any(info["path"] == rel_path for info in files_info):
                    continue

                # Include all shell scripts regardless of other criteria
                is_shell_script = rel_path.endswith(".sh")

                # Explicitly check for example configuration files
                is_example_config = any(
                    ext in rel_path.lower() for ext in [".example", ".template"]
                ) and any(
                    conf in rel_path.lower()
                    for conf in ["application", "config", "properties", "yml", "yaml"]
                )

                # Check if we should analyze this file
                should_analyze = (
                    is_shell_script
                    or is_example_config
                    or any(rel_path.endswith(ext) for ext in analyzable_extensions)
                )

                if not should_analyze:
                    continue

                try:
                    file_stat = os.stat(file_path)
                    if file_stat.st_size > self.MAX_FILE_SIZE:
                        continue

                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    language = self._detect_language(rel_path)
                    is_entry = self._is_entry_point(content, language, rel_path)

                    # For shell scripts, always consider them as config files
                    is_config = is_shell_script or self._is_config_file(rel_path)

                    # Special handling for example config files
                    if is_example_config and not is_config:
                        is_config = True
                        self.logger.info(
                            f"Forced config detection for example file: {rel_path}"
                        )

                    # Track language stats
                    language_stats[language] = language_stats.get(language, 0) + 1

                    # Check for Spring Boot Application
                    if language == "Java" and "@SpringBootApplication" in content:
                        has_spring_boot = True

                    file_info = {
                        "path": rel_path,
                        "language": language,
                        "is_entry_point": is_entry,
                        "is_config": is_config,
                        "size": file_stat.st_size,
                        "is_key_file": False,
                        "content": content,  # Store content for code analysis
                    }

                    files_info.append(file_info)

                    if is_entry:
                        entry_points.append(rel_path)

                    if is_config:
                        config_files.append(rel_path)
                        self.logger.debug(f"Added regular config file: {rel_path}")

                    if is_shell_script:
                        shell_scripts.append(rel_path)
                        # Ensure shell scripts are added to config_files
                        if rel_path not in config_files:
                            config_files.append(rel_path)
                            self.logger.debug(
                                f"Added shell script to config files: {rel_path}"
                            )

                except Exception as e:
                    self.logger.warning(f"Error processing {rel_path}: {str(e)}")

        # Add a reconciliation step to ensure all shell scripts are included in config_files
        for script in shell_scripts + root_shell_scripts + hobo_shell_scripts:
            if script not in config_files:
                config_files.append(script)
                self.logger.debug(
                    f"Added missing shell script to config files: {script}"
                )

        # Rank files by importance
        for file_info in files_info:
            file_info["importance_score"] = self._rank_file_importance(file_info)

        # Sort files by importance for easier access to top files
        sorted_files = sorted(
            files_info, key=lambda x: x.get("importance_score", 0), reverse=True
        )

        # If we have Spring Boot files, override primary language detection to ensure Java
        primary_language = "Java" if has_spring_boot else None

        # Add special configuration files to config_files if they're not already there
        special_config_patterns = [
            "application-env-local.yml.example",
            "application.yml.example",
            "application-dev.yml.example",
        ]

        for file_info in files_info:
            file_path = file_info["path"]
            if (
                any(pattern in file_path.lower() for pattern in special_config_patterns)
                and file_path not in config_files
            ):
                config_files.append(file_path)
                self.logger.info(f"Added special config file: {file_path}")
                # Also mark it as a config file in the file_info
                file_info["is_config"] = True

        # Add entry points and config files to result
        return {
            "files": sorted_files,
            "entry_points": entry_points,
            "config_files": config_files,
            "key_project_files": [
                info["path"] for info in files_info if info.get("is_key_file", False)
            ],
            "language_stats": language_stats,
            "has_spring_boot": has_spring_boot,
            "force_primary_language": primary_language,
            "shell_scripts": shell_scripts,
            "root_shell_scripts": root_shell_scripts,
            "hobo_shell_scripts": hobo_shell_scripts,
        }

    def _is_sonar_file(self, file_path: str) -> bool:
        """Determine if a file is a Sonar-related configuration file.

        Args:
            file_path: Path to the file

        Returns:
            Boolean indicating if the file is a Sonar-related configuration file
        """
        # Convert to lowercase for case-insensitive comparison
        file_path_lower = file_path.lower()

        # Check for common Sonar configuration files
        sonar_patterns = [
            "sonar-project.properties",
            "sonarqube",
            "sonar-scanner",
            ".sonarcloud",
            ".sonarqube",
            ".sonar",
        ]

        return any(pattern in file_path_lower for pattern in sonar_patterns)

    def _is_config_file(self, file_path: str) -> bool:
        """Determine if a file is a configuration file.

        Args:
            file_path: Path to the file

        Returns:
            Boolean indicating if the file is a configuration file
        """
        # Convert to lowercase for case-insensitive comparison
        file_path_lower = file_path.lower()

        # First check if it's a Sonar-related file - we want to identify it as a config
        # but still exclude it from processing via _is_sonar_file
        if self._is_sonar_file(file_path_lower):
            self.logger.debug(f"Identified Sonar config file: {file_path}")
            return True

        # Shell scripts should always be considered configuration files
        if file_path_lower.endswith(".sh"):
            self.logger.debug(f"Identified shell script as config file: {file_path}")
            return True

        # Directly check for application-env-local.yml.example
        if "application-env-local.yml.example" in file_path_lower:
            self.logger.info(f"Detected example config file: {file_path}")
            return True

        # Check for common configuration file extensions
        if any(
            file_path_lower.endswith(ext)
            for ext in [
                ".yml",
                ".yaml",
                ".properties",
                ".xml",
                ".toml",
                ".json",
                ".conf",
                ".ini",
                ".config",
            ]
        ):
            return True

        # Check for example/template configuration files
        if any(
            file_path_lower.endswith(ext)
            for ext in [
                ".example",
                ".template",
                ".sample",
                ".yml.example",
                ".yaml.example",
                ".properties.example",
                ".yml.template",
                ".yaml.template",
                ".properties.template",
            ]
        ):
            self.logger.info(f"Detected example/template config file: {file_path}")
            return True

        # Check for configuration keywords in the path
        config_keywords = [
            "config",
            "settings",
            "application",
            "env",
            "environment",
            "properties",
        ]
        if any(keyword in file_path_lower for keyword in config_keywords):
            return True

        return False

    def _determine_primary_language(self, file_data: Dict[str, Any]) -> str:
        """Determine the primary language used in the repository.

        Args:
            file_data: Dictionary with file information data

        Returns:
            String representing the primary language
        """
        # If we've detected Spring Boot applications, always use Java as primary language
        if file_data.get("force_primary_language"):
            self.logger.debug(
                f"Forced primary language detection: {file_data['force_primary_language']}"
            )
            return file_data["force_primary_language"]

        # Use pre-computed language stats if available
        if "language_stats" in file_data:
            lang_count = file_data["language_stats"]
        else:
            # Otherwise compute from files list
            lang_count = {}
            for file in file_data["files"]:
                if file["language"] != "Unknown":
                    lang_count[file["language"]] = (
                        lang_count.get(file["language"], 0) + 1
                    )

        self.logger.info(f"Language distribution: {lang_count}")

        # Special case: If we have Java files and Spring Boot/Gradle, prioritize Java
        if "Java" in lang_count and (
            "has_spring_boot" in file_data
            or any(f["path"].endswith(".gradle") for f in file_data["files"])
        ):
            self.logger.info(
                "Java identified as primary language due to Spring Boot/Gradle presence"
            )
            return "Java"

        if not lang_count:
            return "Unknown"

        # Use the most frequent language
        return max(lang_count.items(), key=lambda x: x[1])[0]

    def analyze_repository(self, update: bool = True) -> Dict[str, Any]:
        """Analyze the repository structure and content.

        Args:
            update: Whether to update the analysis or use cached results

        Returns:
            Repository information dictionary
        """
        # Check if a non-empty README exists in the root directory
        root_readme_paths = [
            self.config.target_repo / "README.md",
            self.config.target_repo / "Readme.md",
            self.config.target_repo / "readme.md",
        ]

        for path in root_readme_paths:
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():  # If README is not empty
                        self.repo_info = {
                            "name": self.config.target_repo.name,
                            "readme_exists": True,
                            "readme_path": str(path),
                        }
                except Exception as e:
                    self.logger.warning(f"Error reading README at {path}: {str(e)}")

        if self.analyzed and not update:
            formatted_info = self._format_repo_info()
            # Return only the formatted analysis and necessary repo info
            return {
                "name": self.repo_info["name"],
                "primary_language": self.repo_info.get("primary_language", "Unknown"),
                "formatted_analysis": formatted_info,
            }

        # Gather file information
        file_data = self._gather_file_info()
        files_info = file_data["files"]
        shell_scripts = file_data.get("shell_scripts", [])
        config_files = file_data["config_files"]  # Get existing config files

        # Explicitly reconcile shell scripts with config files
        for script in shell_scripts:
            if script not in config_files:
                config_files.append(script)
                self.logger.debug(
                    f"Added missing shell script to config files: {script}"
                )

        # Also include root_shell_scripts and hobo_shell_scripts
        for script in file_data.get("root_shell_scripts", []) + file_data.get(
            "hobo_shell_scripts", []
        ):
            if script not in config_files:
                config_files.append(script)
                self.logger.debug(
                    f"Added root/hobo shell script to config files: {script}"
                )

        # Explicitly scan for example configuration files
        example_config_files = []
        for root, _, files in os.walk(self.config.target_repo):
            for file in files:
                if any(
                    pattern in file.lower() for pattern in [".example", ".template"]
                ):
                    if any(
                        conf in file.lower()
                        for conf in [
                            "application",
                            "config",
                            "properties",
                            "yml",
                            "yaml",
                        ]
                    ):
                        rel_path = os.path.relpath(
                            os.path.join(root, file), self.config.target_repo
                        )
                        if rel_path not in config_files:
                            config_files.append(rel_path)

                        example_config_files.append(rel_path)
                        self.logger.info(f"Added example config file: {rel_path}")

        # Extract language-specific information (to be implemented by subclasses)
        lang_specific_info = self._extract_language_specific_info(files_info)

        # Find and analyze any README files in the repository
        readme_files = []
        readme_contents = {}

        for file_info in files_info:
            file_path = file_info["path"]
            if file_path.lower().endswith("readme.md"):
                readme_files.append(file_path)
                try:
                    content = file_info.get("content", "")
                    if not content:
                        full_path = self.config.target_repo / file_path
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                    readme_contents[file_path] = content
                except Exception as e:
                    self.logger.warning(
                        f"Error reading README at {file_path}: {str(e)}"
                    )

        # Build repository information
        self.repo_info = {
            "name": self.config.target_repo.name,
            "primary_language": self._determine_primary_language(file_data),
            "total_files": len(files_info),
            "entry_points": file_data["entry_points"],
            "config_files": config_files,  # Use the updated config_files list
            "example_config_files": example_config_files,  # Add the example config files
            "key_project_files": file_data.get("key_project_files", []),
            "readme_files": readme_files,
            "readme_contents": readme_contents,
            "file_breakdown": {
                lang: count
                for lang, count in file_data.get("language_stats", {}).items()
            },
            "files": files_info[:50],  # Include top 50 files by importance,
            "has_spring_boot": file_data.get("has_spring_boot", False),
            "shell_scripts": shell_scripts,
            # Add the new file path to content mapping
            "file_contents": {
                f["path"]: f.get("content", "") for f in files_info if "content" in f
            },
            # Include language-specific information
            **lang_specific_info,
        }

        self.analyzed = True

        # Generate analysis text
        self._generate_analysis_text()

        # Return the full repo_info dictionary with formatted analysis
        formatted_info = self._format_repo_info()
        return {**self.repo_info, "formatted_analysis": formatted_info}

    def _extract_language_specific_info(
        self, files_info: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract language-specific information from files.

        Should be overridden by subclasses.

        Args:
            files_info: List of file information dictionaries

        Returns:
            Dictionary with language-specific information
        """
        # Default implementation returns empty dict
        return {}

    def _generate_analysis_text(self) -> None:
        """Generate analysis text from repository information.

        Should be overridden by subclasses.
        """
        # Default implementation does nothing
        pass

    def _format_repo_info(self) -> str:
        """Format repository information as a string.

        Returns:
            Formatted repository information
        """
        if not self.repo_info:
            return "No repository information available."

        info = self.repo_info
        result = [
            f"# Repository Analysis for: {info['name']}",
            f"Primary Language: {info['primary_language']}",
            f"Total Files: {info['total_files']}",
            "\n## Overview",
            info.get("analysis", "No detailed analysis available."),
            "\n## File Breakdown",
        ]

        for lang, count in sorted(
            info["file_breakdown"].items(), key=lambda x: x[1], reverse=True
        ):
            result.append(f"- {lang}: {count} files")

        if info["entry_points"]:
            result.append("\n## Entry Points")
            for entry in info["entry_points"]:
                result.append(f"- {entry}")

        # Separate shell scripts by location
        root_shell_scripts = info.get("root_shell_scripts", [])
        if root_shell_scripts:
            result.append("\n## Root Shell Scripts")
            for script in root_shell_scripts:
                result.append(f"- {script}")

        hobo_shell_scripts = info.get("hobo_shell_scripts", [])
        if hobo_shell_scripts:
            result.append("\n## Hobo Shell Scripts")
            for script in hobo_shell_scripts:
                result.append(f"- {script}")

        return "\n".join(result)
