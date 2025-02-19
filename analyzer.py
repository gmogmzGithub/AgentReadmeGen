"""Repository analysis module."""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from config import GeneratorConfig

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate


class RepositoryAnalyzer:
    """Analyzes repository structure and content."""

    # Define the file types we want to analyze
    ANALYZABLE_EXTENSIONS = {
        # Java ecosystem
        '.java', '.groovy', '.scala', '.gradle', '.properties', '.mvn', '.maven',
        # Python ecosystem
        '.py', '.toml', '.cfg', '.ini',
        # JavaScript/TypeScript ecosystem
        '.js', '.jsx', '.ts', '.tsx', '.json',
        # Web
        '.html', '.css', '.scss', '.sass',
        # Documentation
        '.md', '.rst', '.txt', '.adoc', '.asciidoc',
        # Configuration
        '.yaml', '.yml', '.xml', '.env', '.config', '.conf',
        # Build systems
        '.gradle', '.sbt', '.pom', '.build', '.make', '.mk', '.cmake'
    }

    # Important project files to always include regardless of extension
    KEY_PROJECT_FILES = {
        # General
        'README.md', 'LICENSE', 'CONTRIBUTING.md', 'CHANGELOG.md',
        # Package managers
        'package.json', 'package-lock.json', 'yarn.lock', 'npm-shrinkwrap.json',
        'Pipfile', 'Pipfile.lock', 'requirements.txt', 'setup.py',
        'pom.xml', 'build.gradle', 'build.sbt', 'Cargo.toml',
        'Gemfile', 'Gemfile.lock', 'composer.json', 'composer.lock',
        # Configuration
        '.dockerignore', 'Dockerfile', 'docker-compose.yml',
        'pyproject.toml', 'tox.ini', 'pytest.ini', 'setup.cfg',
        'tsconfig.json', '.eslintrc', '.eslintrc.js', '.eslintrc.json',
        '.babelrc', '.prettierrc', 'webpack.config.js', 'rollup.config.js',
        # CI/CD
        '.gitlab-ci.yml'
        # Environment
        '.env.example', '.env.template', '.nvmrc', '.python-version',
    }

    MAX_FILE_SIZE = 1024 * 100  # 100KB max file size to analyze

    def __init__(self, config: GeneratorConfig) -> None:
        """Initialize the repository analyzer.

        Args:
            config: Generator configuration
        """
        self.config = config
        self.llm = ChatOpenAI(model=config.model, temperature=0)
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
            
            Based on this information, provide a concise analysis of:
            1. What this repository does
            2. Its key components
            3. How it's structured
            4. Any notable features or patterns
            
            Be specific and focus on what can be inferred from the actual codebase structure.
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
            ".bat": "Batch"
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")

    def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
        """Determine if a file is an entry point based on content and language."""
        # Check by language-specific patterns
        patterns = {
            "Python": ['if __name__ == "__main__":', "def main(", "def run("],
            "Java": ["public static void main", "@SpringBootApplication"],
            "JavaScript": ["export default ", "module.exports", "ReactDOM.render"],
            "TypeScript": ["export default ", "createRoot"]
        }

        for pattern in patterns.get(language, []):
            if pattern in content:
                return True

        # Check by filename
        entry_point_files = {
            "Python": ["main.py", "app.py", "cli.py", "run.py"],
            "JavaScript": ["index.js", "main.js", "app.js"],
            "TypeScript": ["index.ts", "main.ts", "app.ts"],
            "Java": ["Application.java", "Main.java"]
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
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        language = self._detect_language(rel_path)
                        is_config = file_name in [
                            'package.json', 'pyproject.toml', 'pom.xml', 'build.gradle',
                            'Pipfile', 'requirements.txt', 'setup.py', 'Gemfile',
                            'composer.json', 'Cargo.toml'
                        ]

                        file_info = {
                            "path": rel_path,
                            "language": language,
                            "is_entry_point": False,  # Key project files usually aren't entry points
                            "is_config": is_config,
                            "size": file_stat.st_size,
                            "is_key_file": True
                        }

                        files_info.append(file_info)
                        if is_config:
                            config_files.append(rel_path)
                except Exception as e:
                    logging.warning(f"Error processing key file {file_path}: {str(e)}")

        # Second pass for regular file discovery
        for root, _, files in os.walk(self.config.target_repo):
            # Skip common directories to ignore
            if any(part in root for part in [".git", "node_modules", "venv", "__pycache__",
                                             "target", "build", "dist"]):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.config.target_repo)

                # Skip if we already processed this file as a key file
                if any(info["path"] == rel_path for info in files_info):
                    continue

                # Check if we should analyze this file
                should_analyze = any(rel_path.endswith(ext) for ext in self.ANALYZABLE_EXTENSIONS)

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
                    is_config = any(rel_path.endswith(ext) for ext in
                                    ['.toml', '.json', '.yml', '.yaml', '.xml', '.properties',
                                     '.ini', '.cfg']) or 'config' in rel_path.lower()

                    file_info = {
                        "path": rel_path,
                        "language": language,
                        "is_entry_point": is_entry,
                        "is_config": is_config,
                        "size": file_stat.st_size,
                        "is_key_file": False
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
            "key_project_files": [info["path"] for info in files_info if info.get("is_key_file", False)]
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
                file_path = os.path.join(self.config.target_repo, file["path"])
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Basic dependency detection based on file type
                if file["path"].endswith("pyproject.toml") or file["path"].endswith("Pipfile"):
                    # Extract Python dependencies
                    import re
                    deps = re.findall(r'([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', content)
                    dependencies.extend([f"{name}=={version}" for name, version in deps])

                elif file["path"].endswith("package.json"):
                    # Extract npm dependencies
                    import json
                    try:
                        pkg_data = json.loads(content)
                        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                        dependencies.extend([f"{name}@{version}" for name, version in deps.items()])
                    except json.JSONDecodeError:
                        pass

                elif file["path"].endswith(("requirements.txt", "requirements.frozen")):
                    # Extract pip requirements
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dependencies.append(line)

            except Exception as e:
                logging.warning(f"Error extracting dependencies from {file['path']}: {str(e)}")

        return dependencies

    def _check_for_gradle(self) -> Dict[str, Any]:
        """Check if this is a Gradle project and identify execution details."""
        gradle_info = {
            "is_gradle": False,
            "has_gradle_wrapper": False,
            "gradle_commands": []
        }

        # Check for Gradle files
        gradle_files = [
            self.config.target_repo / "build.gradle",
            self.config.target_repo / "build.gradle.kts",
            self.config.target_repo / "settings.gradle",
            self.config.target_repo / "settings.gradle.kts"
        ]

        for file in gradle_files:
            if file.exists():
                gradle_info["is_gradle"] = True
                break

        # Check for Gradle wrapper
        gradle_wrapper = self.config.target_repo / "gradlew"
        gradle_wrapper_bat = self.config.target_repo / "gradlew.bat"

        if gradle_wrapper.exists() or gradle_wrapper_bat.exists():
            gradle_info["has_gradle_wrapper"] = True

            # Try to find common tasks by looking in build.gradle files
            gradle_build_files = list(self.config.target_repo.glob("**/build.gradle")) + \
                                 list(self.config.target_repo.glob("**/build.gradle.kts"))

            common_tasks = ["build", "test", "run", "bootRun", "clean"]
            found_tasks = set()

            for build_file in gradle_build_files[:5]:  # Limit to first 5 build files
                try:
                    content = build_file.read_text(encoding='utf-8', errors='ignore')

                    # Look for task definitions or plugins that suggest certain tasks
                    if "apply plugin: 'application'" in content or "id 'application'" in content:
                        found_tasks.add("run")
                    if "apply plugin: 'spring-boot'" in content or "id 'org.springframework.boot'" in content:
                        found_tasks.add("bootRun")
                    if "task" in content and "Test" in content:
                        found_tasks.add("test")

                    # Add standard tasks
                    found_tasks.update(["build", "clean"])

                except Exception as e:
                    logging.warning(f"Error reading Gradle file {build_file}: {e}")

            # Generate command examples using ./gradlew
            gradle_info["gradle_commands"] = [f"./gradlew {task}" for task in found_tasks]

        return gradle_info

    def _check_for_hobo(self) -> Dict[str, Any]:
        """Check if this repository uses the company's Hobo tool."""
        hobo_info = {
            "uses_hobo": False,
            "hobo_directory": None,
            "suggested_commands": []
        }

        # Check for hobo directory
        hobo_dir = self.config.target_repo / "hobo"
        if hobo_dir.exists() and hobo_dir.is_dir():
            hobo_info["uses_hobo"] = True
            hobo_info["hobo_directory"] = "hobo"
            hobo_info["suggested_commands"] = ["hoboRun", "hoboStop", "hoboStatus"]

        return hobo_info

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
            self.config.target_repo / "readme.md"
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
                            "skip_process": True
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

        gradle_info = self._check_for_gradle()
        hobo_info = self._check_for_hobo()

        # Find and analyze any README files in the repository (not just root)
        readme_files = []
        readme_contents = {}

        for file_info in files_info:
            file_path = file_info["path"]
            if file_path.lower().endswith("readme.md"):
                readme_files.append(file_path)
                try:
                    full_path = self.config.target_repo / file_path
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    readme_contents[file_path] = content
                except Exception as e:
                    logging.warning(f"Error reading README at {file_path}: {str(e)}")

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
            "gradle_info": gradle_info,
            "hobo_info": hobo_info,
            "file_breakdown": {lang: sum(1 for f in files_info if f["language"] == lang)
                               for lang in set(f["language"] for f in files_info)}
        }

        self.analyzed = True

        build_system_info = ""
        if gradle_info["is_gradle"]:
            if gradle_info["has_gradle_wrapper"]:
                commands = "\n".join([f"- `{cmd}`" for cmd in gradle_info["gradle_commands"]])
                build_system_info += f"""
        ## Build System: Gradle with Wrapper
        This project uses Gradle with the Gradle Wrapper. Recommended commands:
        {commands}
        Note: Always use `./gradlew` instead of `gradle` to ensure consistent builds.
        """
            else:
                build_system_info += "\n## Build System: Gradle\nThis project uses Gradle."

        if hobo_info["uses_hobo"]:
            build_system_info += f"""
        ## Hobo Deployment
        This project appears to use the company's Hobo tool for containerization.
        You may be able to run it using the `hoboRun` command.
        """

        try:
            file_distribution = "\n".join([
                f"- {lang}: {count} files"
                for lang, count in sorted(self.repo_info['file_breakdown'].items(),
                                          key=lambda x: x[1], reverse=True)
            ])

            entry_points_text = "\n".join([f"- {ep}" for ep in self.repo_info["entry_points"]]) or "None found"
            key_files_text = "\n".join([f"- {kf}" for kf in self.repo_info["key_project_files"]]) or "None found"

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

                readme_list = "\n\n".join([
                    f"## README from {path}:\n{content}"
                    for path, content in readme_contents.items()
                ])

                readme_analysis = self.llm.invoke(
                    readme_prompt.format(readme_list=readme_list)
                ).content

            # Enhanced prompt that includes any README info
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

                Based on this information, provide a comprehensive analysis of:
                1. What this repository does
                2. Its key components and features
                3. How it's structured
                4. Installation and usage patterns
                5. Any notable design patterns or architectural decisions

                Be specific and focus on what can be inferred from the codebase structure
                and any documentation found.
                """
            )

            # Prepare README section based on whether we found any READMEs
            if readme_analysis:
                readme_section = f"README Analysis:\n{readme_analysis}"
            else:
                readme_section = "No README files found in the repository."

            analysis_text = analysis_prompt.format(
                repo_name=self.repo_info["name"],
                primary_language=self.repo_info["primary_language"],
                total_files=self.repo_info["total_files"],
                readme_section=readme_section,
                key_files=key_files_text,
                file_distribution=file_distribution,
                entry_points=entry_points_text
            )

            enhanced_analysis = self.llm.invoke(analysis_text).content
            self.repo_info["analysis"] = enhanced_analysis

        except Exception as e:
            logging.error(f"Error generating repository analysis: {e}")
            self.repo_info["analysis"] = "Analysis could not be generated due to an error."

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

        for lang, count in sorted(info['file_breakdown'].items(), key=lambda x: x[1], reverse=True):
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