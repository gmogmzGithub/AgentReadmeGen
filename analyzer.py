"""Enhanced repository analysis module."""

import os
import logging
from pathlib import Path
import re
from typing import Dict, List, Any

from config import GeneratorConfig
from code_understanding_analyzer import CodeUnderstandingAnalyzer

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from openai import OpenAI


class RepositoryAnalyzer:
    """Analyzes repository structure and content with enhanced code understanding."""

    # Define the file types we want to analyze
    ANALYZABLE_EXTENSIONS = {
        # Java
        ".java",
        ".groovy",
        ".scala",
        ".gradle",
        ".properties",
        ".mvn",
        ".maven",
        # Python
        ".py",
        ".toml",
        ".cfg",
        ".ini",
        # JavaScript/TypeScript
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".json",
        # Web
        ".html",
        ".css",
        ".scss",
        ".sass",
        # Documentation
        ".md",
        ".rst",
        ".txt",
        ".adoc",
        ".asciidoc",
        # Configuration
        ".yaml",
        ".yml",
        ".xml",
        ".env",
        ".config",
        ".conf",
        # Build systems
        ".gradle",
        ".sbt",
        ".pom",
        ".build",
        ".make",
        ".mk",
        ".cmake",
    }

    # Important project files to always include regardless of extension
    KEY_PROJECT_FILES = {
        # General
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        # Package managers
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "npm-shrinkwrap.json",
        "Pipfile",
        "Pipfile.lock",
        "requirements.txt",
        "setup.py",
        "pom.xml",
        "build.gradle",
        "build.sbt",
        "Cargo.toml",
        "Gemfile",
        "Gemfile.lock",
        "composer.json",
        "composer.lock",
        # Configuration
        ".dockerignore",
        "Dockerfile",
        "docker-compose.yml",
        "pyproject.toml",
        "tox.ini",
        "pytest.ini",
        "setup.cfg",
        "tsconfig.json",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.json",
        ".babelrc",
        ".prettierrc",
        "webpack.config.js",
        "rollup.config.js",
        # CI/CD
        ".gitlab-ci.yml",
        # Environment
        ".env.example",
        ".env.template",
        ".nvmrc",
        ".python-version",
    }

    MAX_FILE_SIZE = 1024 * 100  # 100KB max file size to analyze

    def __init__(self, config: GeneratorConfig) -> None:
        """Initialize the repository analyzer.

        Args:
            config: Generator configuration
        """
        self.config = config
        self.llm = ChatOpenAI(model=config.model, temperature=0)
        self.code_analyzer = CodeUnderstandingAnalyzer(self.llm)
        self.repo_info = {}
        self.analyzed = False

        self.analysis_prompt = PromptTemplate.from_template(
            """Analyze the following repository information to understand its purpose and structure:
            
            Repository name: {repo_name}
            Primary language: {primary_language}
            Total Files: {total_files}
            
            File Distribution:
            {file_distribution}
            
            Entry Points:
            {entry_points}
            
            # Deep Code Analysis
            {code_understanding}
            
            Based on this information, provide a concise analysis of:
            1. What this repository does
            2. Its key components
            3. How it's structured
            4. Any notable features or patterns
            
            Be specific and focus on what can be inferred from the actual codebase structure and functionality.
            """
        )

    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language based on file extension."""
        ext_map = {
            ".py": "Python",
            ".java": "Java",
            ".groovy": "Groovy",
            ".scala": "Scala",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".json": "JSON",
            ".md": "Markdown",
            ".toml": "TOML",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
            ".properties": "Properties",
            ".gradle": "Gradle",
            ".sh": "Shell",
            ".bat": "Batch",
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")

    def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
        """Determine if a file is an entry point based on content and language."""
        # Language-specific patterns
        patterns = {
            "Python": ['if __name__ == "__main__":', "def main(", "def run("],
            "Java": ["public static void main", "@SpringBootApplication"],
            "JavaScript": ["export default ", "module.exports", "ReactDOM.render"],
            "TypeScript": ["export default ", "createRoot"],
        }

        for pattern in patterns.get(language, []):
            if pattern in content:
                return True

        # Check by filename
        entry_point_files = {
            "Python": ["main.py", "app.py", "cli.py", "run.py"],
            "JavaScript": ["index.js", "main.js", "app.js"],
            "TypeScript": ["index.ts", "main.ts", "app.ts"],
            "Java": ["Application.java", "Main.java"],
        }

        filename = Path(file_path).name
        for entry_file in entry_point_files.get(language, []):
            if filename == entry_file:
                return True

        return False

    def _gather_file_info(self) -> Dict[str, Any]:
        """Gather information about files in the repository."""
        files_info = []
        entry_points = []
        config_files = []

        # First pass to identify key project files regardless of extension
        for file_name in self.KEY_PROJECT_FILES:
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
                        is_config = file_name in [
                            "package.json",
                            "pyproject.toml",
                            "pom.xml",
                            "build.gradle",
                            "Pipfile",
                            "requirements.txt",
                            "setup.py",
                            "Gemfile",
                            "composer.json",
                            "Cargo.toml",
                        ]

                        file_info = {
                            "path": rel_path,
                            "language": language,
                            "is_entry_point": False,  # Key project files usually aren't entry points
                            "is_config": is_config,
                            "size": file_stat.st_size,
                            "is_key_file": True,
                            "content": content,  # Store content for code analysis
                        }

                        files_info.append(file_info)
                        if is_config:
                            config_files.append(rel_path)
                except Exception as e:
                    logging.warning(f"Error processing key file {file_path}: {str(e)}")

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
                ]
            ):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.config.target_repo)

                # Skip if we already processed this file as a key file
                if any(info["path"] == rel_path for info in files_info):
                    continue

                # Check if we should analyze this file
                should_analyze = any(
                    rel_path.endswith(ext) for ext in self.ANALYZABLE_EXTENSIONS
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

                    # Determine if it's a config file
                    is_config = (
                        any(
                            rel_path.endswith(ext)
                            for ext in [
                                ".toml",
                                ".json",
                                ".yml",
                                ".yaml",
                                ".xml",
                                ".properties",
                                ".ini",
                                ".cfg",
                            ]
                        )
                        or "config" in rel_path.lower()
                    )

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

                except Exception as e:
                    logging.warning(f"Error processing {rel_path}: {str(e)}")

        return {
            "files": files_info,
            "entry_points": entry_points,
            "config_files": config_files,
            "key_project_files": [
                info["path"] for info in files_info if info.get("is_key_file", False)
            ],
        }

    def _determine_primary_language(self, files_info: List[Dict[str, Any]]) -> str:
        """Determine the primary language used in the repository."""
        lang_count = {}
        for file in files_info:
            if file["language"] != "Unknown":
                lang_count[file["language"]] = lang_count.get(file["language"], 0) + 1

        if not lang_count:
            return "Unknown"

        return max(lang_count.items(), key=lambda x: x[1])[0]

    def _find_dependencies(self, files_info: List[Dict[str, Any]]) -> List[str]:
        """Find dependencies from configuration files."""
        dependencies = []

        for file in files_info:
            if not file["is_config"]:
                continue

            try:
                content = file.get("content", "")
                if not content:
                    file_path = os.path.join(self.config.target_repo, file["path"])
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                # Basic dependency detection based on file type
                if file["path"].endswith("pyproject.toml") or file["path"].endswith(
                    "Pipfile"
                ):
                    # Extract Python dependencies
                    deps = re.findall(
                        r'([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', content
                    )
                    dependencies.extend(
                        [f"{name}=={version}" for name, version in deps]
                    )

                elif file["path"].endswith("package.json"):
                    # Extract npm dependencies
                    import json

                    try:
                        pkg_data = json.loads(content)
                        deps = {
                            **pkg_data.get("dependencies", {}),
                            **pkg_data.get("devDependencies", {}),
                        }
                        dependencies.extend(
                            [f"{name}@{version}" for name, version in deps.items()]
                        )
                    except json.JSONDecodeError:
                        pass

                elif file["path"].endswith(("requirements.txt", "requirements.frozen")):
                    # Extract pip requirements
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            dependencies.append(line)

            except Exception as e:
                logging.warning(
                    f"Error extracting dependencies from {file['path']}: {str(e)}"
                )

        return dependencies

    def _detect_build_system(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect the build system used in the repository."""
        build_system = {"type": "unknown", "has_wrapper": False, "files": []}

        # Check for build system files
        build_system_indicators = {
            "gradle": [
                ".gradle",
                "build.gradle",
                "gradle.properties",
                "settings.gradle",
                "gradlew",
            ],
            "maven": ["pom.xml", "mvnw"],
            "npm": ["package.json", "yarn.lock", "package-lock.json"],
            "pip": ["setup.py", "requirements.txt", "Pipfile", "pyproject.toml"],
            "cargo": ["Cargo.toml"],
            "make": ["Makefile", "makefile"],
            "bazel": ["BUILD.bazel", "WORKSPACE"],
        }

        found_systems = {}

        for file_info in files_info:
            file_path = file_info["path"]
            file_name = os.path.basename(file_path)

            for system, indicators in build_system_indicators.items():
                if file_name in indicators or any(
                    file_path.endswith(ext) for ext in indicators
                ):
                    found_systems[system] = found_systems.get(system, 0) + 1
                    if system not in build_system["files"]:
                        build_system["files"].append(file_path)

        if found_systems:
            # Determine primary build system
            primary_system = max(found_systems.items(), key=lambda x: x[1])[0]
            build_system["type"] = primary_system

            # Check for wrappers
            if primary_system == "gradle" and any(
                "gradlew" in file for file in build_system["files"]
            ):
                build_system["has_wrapper"] = True
            elif primary_system == "maven" and any(
                "mvnw" in file for file in build_system["files"]
            ):
                build_system["has_wrapper"] = True

        return build_system

    def _detect_custom_tools(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect custom tools used in the repository."""
        custom_tools = []

        # Check for common custom tools and directories
        custom_tool_indicators = {
            "hobo": ["hobo", "hobo.properties", "hobo.yml"],
            "docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
            "kubernetes": [".k8s", "k8s", "kubernetes", "helm"],
            "terraform": [".tf", "terraform", ".tfvars"],
            "jenkins": ["Jenkinsfile"],
            "gitlab-ci": [".gitlab-ci.yml"],
            "github-actions": [".github/workflows"],
        }

        for file_info in files_info:
            file_path = file_info["path"]
            file_name = os.path.basename(file_path)

            for tool, indicators in custom_tool_indicators.items():
                if (
                    file_name in indicators
                    or any(file_path.endswith(ext) for ext in indicators)
                    or any(part in file_path for part in indicators)
                ):
                    if tool not in custom_tools:
                        custom_tools.append(tool)

        return {"custom_tools": custom_tools}

    def analyze_repository(self, update: bool = True) -> str:
        """Analyze the repository structure and content.

        Args:
            update: Whether to update the analysis or use cached results

        Returns:
            Repository information in a string format or a message indicating an existing README
        """
        # Check if a non-empty README exists in the root directory
        root_readme_paths = [
            self.config.target_repo / "README.md",
            self.config.target_repo / "Readme.md",
            self.config.target_repo / "readme.md",
        ]

        for path in root_readme_paths:
            if path.exists() and path.is_file():
                # Check if README is not empty
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():  # If README is not empty
                        self.repo_info = {
                            "name": self.config.target_repo.name,
                            "readme_exists": True,
                            "readme_path": str(path),
                            "skip_process": True,
                        }
                        return f"Non-empty README already exists at {path}. Skipping analysis."
                except Exception as e:
                    logging.warning(f"Error reading README at {path}: {str(e)}")

        # If we reach here, either no README exists or it's empty
        if self.analyzed and not update:
            return self._format_repo_info()

        # Gather file information
        file_data = self._gather_file_info()
        files_info = file_data["files"]

        # Detect build system and custom tools
        build_system = self._detect_build_system(files_info)
        custom_tools = self._detect_custom_tools(files_info)

        # Find and analyze any README files in the repository (not just root)
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
                    logging.warning(f"Error reading README at {file_path}: {str(e)}")

        # Perform deep code analysis
        code_understanding = self.code_analyzer.analyze_code_understanding(
            files_info, self.config.target_repo
        )

        # Analyze repository
        self.repo_info = {
            "name": self.config.target_repo.name,
            "primary_language": self._determine_primary_language(files_info),
            "total_files": len(files_info),
            "entry_points": file_data["entry_points"],
            "config_files": file_data["config_files"],
            "key_project_files": file_data.get("key_project_files", []),
            "dependencies": self._find_dependencies(files_info),
            "readme_files": readme_files,
            "readme_contents": readme_contents,
            "build_system": build_system,
            "custom_tools": custom_tools,
            "code_understanding": code_understanding,
            "file_breakdown": {
                lang: sum(1 for f in files_info if f["language"] == lang)
                for lang in set(f["language"] for f in files_info)
            },
        }

        self.analyzed = True

        try:
            file_distribution = "\n".join(
                [
                    f"- {lang}: {count} files"
                    for lang, count in sorted(
                        self.repo_info["file_breakdown"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ]
            )

            entry_points_text = (
                "\n".join([f"- {ep}" for ep in self.repo_info["entry_points"]])
                or "None found"
            )
            key_files_text = (
                "\n".join([f"- {kf}" for kf in self.repo_info["key_project_files"]])
                or "None found"
            )

            # Handle READMEs found in the repository (not in root)
            readme_analysis = ""
            if readme_contents:
                readme_prompt = PromptTemplate.from_template(
                    """Analyze the following README files found in the repository:

                    {readme_list}

                    Extract key information about:
                    1. Project purpose
                    2. Features and functionality
                    3. Installation instructions
                    4. Usage examples
                    5. Dependencies
                    6. Architecture

                    Provide a concise summary of the information found.
                    """
                )

                readme_list = "\n\n".join(
                    [
                        f"## README from {path}:\n{content}"
                        for path, content in readme_contents.items()
                    ]
                )

                response = self.llm.invoke(
                    readme_prompt.format(readme_list=readme_list)
                )
                readme_analysis = response.content  # Extract content from AIMessage

            # Enhanced prompt that includes code understanding
            analysis_prompt = PromptTemplate.from_template(
                """Analyze the following repository information to understand its purpose and structure:

                Repository name: {repo_name}
                Primary language: {primary_language}
                Total Files: {total_files}

                {readme_section}

                Key Project Files:
                {key_files}

                File Distribution:
                {file_distribution}

                Entry Points:
                {entry_points}

                Build System: {build_system}
                
                Custom Tools: {custom_tools}

                # Deep Code Analysis
                {code_understanding}

                Based on this information, provide a comprehensive analysis of:
                1. What this repository does
                2. Its key components and features
                3. How it's structured
                4. Installation and usage patterns
                5. Any notable design patterns or architectural decisions

                Be specific and focus on what can be inferred from the codebase structure,
                actual functionality, and any documentation found.
                """
            )

            # Prepare README section based on whether we found any READMEs
            if readme_analysis:
                readme_section = f"README Analysis:\n{readme_analysis}"
            else:
                readme_section = "No README files found in the repository."

            # Prepare build system info
            build_system_text = f"{build_system['type'].capitalize()}"
            if build_system["has_wrapper"]:
                build_system_text += " with wrapper"

            # Prepare custom tools info
            custom_tools_text = ", ".join(custom_tools.get("custom_tools", []))
            if not custom_tools_text:
                custom_tools_text = "None detected"

            analysis_text = analysis_prompt.format(
                repo_name=self.repo_info["name"],
                primary_language=self.repo_info["primary_language"],
                total_files=self.repo_info["total_files"],
                readme_section=readme_section,
                key_files=key_files_text,
                file_distribution=file_distribution,
                entry_points=entry_points_text,
                build_system=build_system_text,
                custom_tools=custom_tools_text,
                code_understanding=code_understanding,
            )

            response = self.llm.invoke(analysis_text)
            enhanced_analysis = response.content
            self.repo_info["analysis"] = enhanced_analysis

        except Exception as e:
            logging.error(f"Error generating repository analysis: {e}")
            self.repo_info["analysis"] = (
                "Analysis could not be generated due to an error."
            )

        return self._format_repo_info()

    def _format_repo_info(self) -> str:
        """Format repository information as a string."""
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

        if info["dependencies"]:
            result.append("\n## Dependencies")
            # Limit to top 10 dependencies to avoid overwhelming the prompt
            for dep in info["dependencies"][:10]:
                result.append(f"- {dep}")
            if len(info["dependencies"]) > 10:
                result.append(f"- ... and {len(info['dependencies']) - 10} more")

        return "\n".join(result)
