"""Java/Gradle/Spring Boot repository analysis module."""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any

from src.analyzers.base_analizer import BaseAnalyzer


class JavaAnalyzer(BaseAnalyzer):
    """Analyzes Java/Gradle/Spring Boot repository structure and content."""

    def _get_analyzable_extensions(self) -> set:
        """Get file extensions that should be analyzed for Java projects.

        Returns:
            Set of file extensions to analyze.
        """
        return {
            # Java
            ".java",
            ".gradle",
            ".properties",
            ".yml",
            ".yaml",
            ".sh",
        }

    def _get_language_specific_key_files(self) -> set:
        """Get Java-specific key files to always include.

        Returns:
            Set of key filenames to always include.
        """
        return {
            # Java/Gradle specific
            "build.gradle",
            "settings.gradle",
            "gradle.properties",
            # Spring Boot specific
            "application.properties",
            "application.yml",
            "application-dev.properties",
            "application-dev.yml",
            # Example configuration files (add these)
            "application-env-local.yml.example",
            "application-env-local.properties.example",
            "application.yml.example",
            "application.properties.example",
            "application-dev.yml.example",
            "application-dev.properties.example",
            # Other environment-specific configurations
            "application-test.yml",
            "application-test.properties",
            "application-prod.yml",
            "application-prod.properties",
        }

    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language based on file extension for Java projects.

        Args:
            file_path: Path to the file

        Returns:
            String representing the detected language
        """
        ext_map = {
            ".java": "Java",
            ".gradle": "Gradle",
            ".properties": "Properties",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")

    def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
        """Determine if a file is an entry point for Java/Spring Boot projects.

        Args:
            content: File content
            language: Detected language
            file_path: Path to the file

        Returns:
            Boolean indicating if the file is an entry point
        """
        # Java specific patterns
        if language == "Java":
            # Spring Boot application
            if re.search(r"@SpringBootApplication", content):
                self.logger.debug(f"Found Spring Boot entry point: {file_path}")
                return True

            # Main method
            if re.search(
                r"public\s+static\s+void\s+main\s*\(\s*String\s*\[\s*\]\s*\w+\s*\)",
                content,
            ):
                self.logger.info(f"Found Java main method entry point: {file_path}")
                return True

        # Gradle build files
        elif language == "Gradle" or "gradle" in file_path.lower():
            # Look for application plugin or Spring Boot plugin
            if re.search(
                r'apply\s+plugin\s*:\s*[\'"](?:application|org\.springframework\.boot)[\'"]',
                content,
            ) or re.search(
                r'plugins\s*{\s*id\s*\([\'"](?:application|org\.springframework\.boot)[\'"]\)',
                content,
            ):
                self.logger.info(f"Found Gradle application configuration: {file_path}")
                return True

        return False

    def _rank_file_importance(self, file_info: Dict[str, Any]) -> int:
        """Rank a file's importance specifically for Java/Gradle projects.

        Args:
            file_info: Dictionary with file information

        Returns:
            Integer score representing file importance
        """
        # First get the base score from parent class
        score = super()._rank_file_importance(file_info)

        path = file_info.get("path", "").lower()
        content = file_info.get("content", "")

        # Spring Boot application classes are crucial
        if content and re.search(r"@SpringBootApplication", content):
            score += 110

        # Priority based on Java filename patterns
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

        # Gradle files
        if path.endswith(".gradle") or "gradle" in path:
            score += 75

        # Spring config files
        if path.endswith(".properties") or path.endswith(".yml"):
            if "application" in path:
                score += 70
                # Higher priority for environment-specific configs
                if "local" in path or "dev" in path:
                    score += 10
                # Even higher priority for example files that show required configuration
                if path.endswith((".example", ".template")):
                    score += 100

        # Shell scripts
        if path.endswith(".sh"):
            score += 65  # High priority for shell scripts

        # Dockerfile and docker-compose
        if "dockerfile" in path.lower():
            score += 70
        elif "docker-compose.yml" in path.lower():
            score += 75

        # Hobo-related files and directories
        if "hobo" in path:
            score += 80

        # Check content for key indicators (if content is available)
        if content:
            # For Java files
            if path.endswith(".java"):
                # Spring annotations are important
                spring_annotations = re.findall(
                    r"@(Controller|RestController|Service|Repository|Component|Configuration|SpringBootApplication)",
                    content,
                )
                score += len(spring_annotations) * 10

                # Main method is important
                if re.search(r"public\s+static\s+void\s+main", content):
                    score += 30

                # REST endpoints are important
                rest_endpoints = re.findall(
                    r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)",
                    content,
                )
                score += len(rest_endpoints) * 8

            # For Gradle files
            elif path.endswith(".gradle"):
                # Spring Boot plugin is important
                if re.search(r"org\.springframework\.boot", content):
                    score += 25

                # Application plugin is important
                if re.search(r"application|java", content):
                    score += 20

                # Custom tasks are important
                custom_tasks = re.findall(r"task\s+(\w+)", content)
                score += len(custom_tasks) * 5

        return score

    def _generate_analysis_text(self) -> None:
        """Generate analysis text from repository information."""
        if not self.repo_info:
            self.repo_info["analysis"] = "No repository information available."
            return

        # Prepare information for analysis summary
        info = self.repo_info

        # Create file distribution text
        file_distribution = "\n".join(
            [
                f"- {lang}: {count} files"
                for lang, count in sorted(
                    info["file_breakdown"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ]
        )

        # Create entry points text
        entry_points_text = (
            "\n".join([f"- {ep}" for ep in info["entry_points"]]) or "None found"
        )

        # Extract example configuration files from key project files
        example_configs = [
            kf
            for kf in info["key_project_files"]
            if any(ext in kf.lower() for ext in [".example", ".template"])
        ]

        # Regular configuration files (non-examples)
        regular_configs = [
            kf
            for kf in info["key_project_files"]
            if (
                kf.endswith((".properties", ".yml", ".yaml"))
                and not any(ext in kf.lower() for ext in [".example", ".template"])
            )
        ]

        # Other key files
        other_key_files = [
            kf
            for kf in info["key_project_files"]
            if kf not in example_configs and kf not in regular_configs
        ]

        # Create key files texts by category
        example_configs_text = (
            "\n".join([f"- {kf}" for kf in example_configs])
            if example_configs
            else "None found"
        )

        regular_configs_text = (
            "\n".join([f"- {kf}" for kf in regular_configs])
            if regular_configs
            else "None found"
        )

        other_key_files_text = (
            "\n".join([f"- {kf}" for kf in other_key_files])
            if other_key_files
            else "None found"
        )

        # Build system info
        build_system = info.get("build_system", {})
        build_system_text = f"{build_system.get('type', 'Unknown').capitalize()}"
        if build_system.get("has_wrapper"):
            build_system_text += " with wrapper"

        # Custom tools info
        custom_tools = info.get("custom_tools", {})
        custom_tools_text = (
            ", ".join(custom_tools.get("custom_tools", [])) or "None detected"
        )

        # Spring Boot info
        spring_boot_text = ""
        if info.get("has_spring_boot", False):
            spring_boot_text = "\nThis is a Spring Boot application."

        # Root shell scripts info
        root_shell_scripts_text = ""
        root_shell_scripts = build_system.get("shell_scripts", [])
        if root_shell_scripts:
            root_shell_scripts_text = "\n\nRoot Shell Scripts:\n"
            for script in root_shell_scripts:
                root_shell_scripts_text += f"- {script}\n"

        # Add build system commands
        build_commands_text = ""
        if build_system.get("commands"):
            build_commands_text = "\n\nBuild System Commands:\n"
            for cmd_name, cmd_value in build_system.get("commands", {}).items():
                if isinstance(cmd_value, list):
                    # For commands that are lists
                    for cmd in cmd_value:
                        build_commands_text += f"- {cmd_name}: `{cmd}`\n"
                else:
                    # For commands that are strings
                    build_commands_text += f"- {cmd_name}: `{cmd_value}`\n"

        # Hobo info
        hobo_text = ""
        hobo_config = info.get("hobo_config", {})
        if hobo_config.get("enabled"):
            hobo_text = "\n\nHobo Configuration:\n"
            if hobo_config.get("has_docker_compose"):
                hobo_text += "- Uses docker-compose\n"
            if hobo_config.get("has_dockerfile"):
                hobo_text += "- Uses Dockerfile\n"
            if hobo_config.get("services"):
                hobo_text += (
                    f"- Services: {', '.join(hobo_config.get('services', []))}\n"
                )

            # Add hobo shell scripts section
            hobo_shell_scripts = hobo_config.get("shell_scripts", [])
            if hobo_shell_scripts:
                hobo_text += "\nHobo Shell Scripts:\n"
                for script in hobo_shell_scripts:
                    hobo_text += f"- {script}\n"

            # Add run scripts
            run_scripts = hobo_config.get("run_scripts", [])
            if run_scripts:
                hobo_text += "\nRun scripts:\n"
                for script in run_scripts:
                    hobo_text += f"- {script}\n"

            # Add auxiliary scripts
            aux_scripts = hobo_config.get("auxiliary_scripts", [])
            if aux_scripts:
                hobo_text += "\nAuxiliary scripts:\n"
                for script in aux_scripts:
                    hobo_text += f"- {script}\n"

            # Add start/stop commands
            hobo_commands = hobo_config.get("commands", {})
            if hobo_commands:
                if hobo_commands.get("start"):
                    hobo_text += "\nStart commands:\n"
                    for cmd in hobo_commands.get("start", []):
                        hobo_text += f"- `{cmd}`\n"

                if hobo_commands.get("stop"):
                    hobo_text += "\nStop commands:\n"
                    for cmd in hobo_commands.get("stop", []):
                        hobo_text += f"- `{cmd}`\n"

        api_patterns_text = ""
        if "api_patterns" in info:
            api_patterns = info.get("api_patterns", [])
            if api_patterns:
                api_patterns_text = "\n\n### API Endpoints:\n"
                # Group by controller/type
                endpoints_by_type = {}
                for pattern in api_patterns:
                    pattern_type = pattern.get("type", "Other")
                    if pattern_type not in endpoints_by_type:
                        endpoints_by_type[pattern_type] = []
                    endpoints_by_type[pattern_type].append(pattern)

                # Format each type
                for pattern_type, patterns in endpoints_by_type.items():
                    api_patterns_text += f"\n**{pattern_type}**:\n"
                    for pattern in patterns:
                        if "endpoint" in pattern and "method" in pattern:
                            api_patterns_text += (
                                f"- {pattern['method']} {pattern['endpoint']}\n"
                            )
                        elif "name" in pattern:
                            api_patterns_text += f"- {pattern['name']}\n"
                        elif "repository" in pattern:
                            api_patterns_text += (
                                f"- Repository: {pattern['repository']}\n"
                            )

        usage_patterns_text = ""
        if "usage_patterns" in info:
            usage_patterns = info.get("usage_patterns", {})
            if usage_patterns:
                usage_patterns_text = "\n\n### Usage Patterns:\n"

                # Add specific commands if available
                if "commands" in usage_patterns and usage_patterns["commands"]:
                    usage_patterns_text += "\n**Commands**:\n"
                    for cmd in usage_patterns["commands"]:
                        usage_patterns_text += f"- `{cmd}`\n"

                # Add API patterns if available
                if "api_patterns" in usage_patterns and usage_patterns["api_patterns"]:
                    usage_patterns_text += "\n**API Usage**:\n"
                    # Group by type
                    api_by_type = {}
                    for api in usage_patterns["api_patterns"]:
                        api_type = api.get("type", "Other")
                        if api_type not in api_by_type:
                            api_by_type[api_type] = []
                        api_by_type[api_type].append(api)

                    # Format each type
                    for api_type, apis in api_by_type.items():
                        usage_patterns_text += f"- {api_type}: "
                        usage_patterns_text += ", ".join(
                            [
                                api.get("name", api.get("endpoint", "Unknown"))
                                for api in apis
                            ]
                        )
                        usage_patterns_text += "\n"

                # Add configuration patterns if available
                if (
                    "configuration" in usage_patterns
                    and usage_patterns["configuration"]
                ):
                    usage_patterns_text += "\n**Configuration**:\n"
                    for config in usage_patterns["configuration"]:
                        usage_patterns_text += f"- {config.get('path', 'Unknown')} ({config.get('format', 'Unknown')})\n"
                        if "required_fields" in config and config["required_fields"]:
                            usage_patterns_text += f"  Required: {', '.join(config['required_fields'][:5])}"
                            if len(config["required_fields"]) > 5:
                                usage_patterns_text += (
                                    f" and {len(config['required_fields']) - 5} more"
                                )
                            usage_patterns_text += "\n"

        # Create the analysis summary with the enhanced information
        analysis_text = f"""
    ## Java/Gradle Repository Analysis

    This Java repository uses {build_system_text} build system.{spring_boot_text}
    ### Key Components:
    {other_key_files_text}

    ### Entry Points:
    {entry_points_text}

    ### Configuration Files:
    {regular_configs_text}

    ### Example Configuration Files:
    {example_configs_text}

    ### File Distribution:
    {file_distribution}

    ### Build System:
    - Type: {build_system_text}
    - Commands:{build_commands_text}

    ### Tools and Technologies:
    {custom_tools_text}
    {root_shell_scripts_text}
    {hobo_text}
    {api_patterns_text}
    {usage_patterns_text}
    """

        # Set the analysis in the repo_info dictionary
        self.repo_info["analysis"] = analysis_text.strip()

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

        # Add a "Quick Start" section with entry points and key commands
        result.append("\n## Quick Start")
        # Add entry points
        if info["entry_points"]:
            result.append("### Entry Points")
            for entry in info["entry_points"][:3]:  # Limit to top 3
                result.append(f"- {entry}")
            if len(info["entry_points"]) > 3:
                result.append(
                    f"- ... and {len(info['entry_points']) - 3} more entry points"
                )

        # Add build commands
        build_system = info.get("build_system", {})
        if build_system and build_system.get("commands"):
            result.append("\n### Build Commands")
            for cmd_name, cmd_value in build_system.get("commands", {}).items():
                if isinstance(cmd_value, list):
                    # For commands that are lists
                    for i, cmd in enumerate(cmd_value):
                        if i < 3:  # Limit to top 3 commands per type
                            result.append(f"- {cmd_name}: `{cmd}`")
                    if len(cmd_value) > 3:
                        result.append(
                            f"  ... and {len(cmd_value) - 3} more {cmd_name} commands"
                        )
                else:
                    # For commands that are strings
                    result.append(f"- {cmd_name}: `{cmd_value}`")

        # Add Hobo commands if available
        hobo_config = info.get("hobo_config", {})
        if hobo_config and hobo_config.get("enabled"):
            result.append("\n### Hobo Commands")
            for cmd_type, cmds in hobo_config.get("commands", {}).items():
                if cmds:
                    for i, cmd in enumerate(cmds[:3]):  # Limit to top 3
                        result.append(f"- {cmd_type}: `{cmd}`")
                    if len(cmds) > 3:
                        result.append(
                            f"  ... and {len(cmds) - 3} more {cmd_type} commands"
                        )

        # Add dependencies (limit to top 10)
        if info.get("dependencies"):
            result.append("\n## Dependencies")
            for dep in info["dependencies"][:10]:
                result.append(f"- {dep}")
            if len(info["dependencies"]) > 10:
                result.append(
                    f"- ... and {len(info['dependencies']) - 10} more dependencies"
                )

        # Add API endpoints if available
        if info.get("api_patterns"):
            result.append("\n## API Endpoints")
            endpoint_count = 0
            for pattern in info["api_patterns"][:10]:  # Limit to top 10
                if "endpoint" in pattern and "method" in pattern:
                    result.append(f"- {pattern['method']} {pattern['endpoint']}")
                    endpoint_count += 1
                elif "name" in pattern:
                    result.append(f"- Controller: {pattern['name']}")
                elif "repository" in pattern:
                    result.append(f"- Repository: {pattern['repository']}")
            if len(info["api_patterns"]) > 10:
                result.append(
                    f"- ... and {len(info['api_patterns']) - 10} more endpoints/controllers"
                )

        # Add project purpose if available
        if "project_purpose" in info and info["project_purpose"]:
            result.append("\n## Project Purpose")
            result.append(info["project_purpose"])

        # Add usage instructions if available from usage patterns
        if "usage_patterns" in info and "llm_analysis" in info["usage_patterns"]:
            result.append("\n## Usage Instructions")
            result.append(
                info["usage_patterns"]["llm_analysis"][:500]
            )  # Limit to avoid overwhelming
            if len(info["usage_patterns"]["llm_analysis"]) > 500:
                result.append("... (see detailed analysis for more)")

        return "\n".join(result)

    def _extract_language_specific_info(
        self, files_info: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Java/Gradle specific information from files.

        Args:
            files_info: List of file information dictionaries

        Returns:
            Dictionary with Java-specific information
        """
        # Extract information specific to Java/Gradle/Spring Boot
        java_files = [f["path"] for f in files_info if f["language"] == "Java"]
        gradle_files = [
            f["path"]
            for f in files_info
            if f["language"] == "Gradle" or f["path"].endswith(".gradle")
        ]

        # Filter shell scripts to EXCLUDE hobo shell scripts
        hobo_config = self._detect_hobo_configuration(self.config.target_repo)
        hobo_shell_scripts = hobo_config.get("shell_scripts", [])

        # Only include shell scripts that aren't in hobo directories
        shell_scripts = [
            f["path"]
            for f in files_info
            if f["path"].endswith(".sh")
            and not any(f["path"].startswith("hobo/") for path in hobo_shell_scripts)
        ]

        build_system = self._detect_build_system(files_info)
        dependencies = self._find_dependencies(files_info)
        custom_tools = self._detect_custom_tools(files_info)

        return {
            "java_files": java_files,
            "gradle_files": gradle_files,
            "shell_scripts": shell_scripts,  # This now excludes hobo shell scripts
            "build_system": build_system,
            "hobo_config": hobo_config,
            "dependencies": dependencies,
            "custom_tools": custom_tools,
        }

    def _find_dependencies(self, files_info: List[Dict[str, Any]]) -> List[str]:
        """Find dependencies from configuration files for Java/Gradle projects.

        Args:
            files_info: List of file information dictionaries

        Returns:
            List of dependency strings
        """
        dependencies = []

        # Look for Gradle dependencies
        for file in files_info:
            if not file["is_config"]:
                continue

            try:
                content = file.get("content", "")
                if not content:
                    file_path = os.path.join(self.config.target_repo, file["path"])
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                if file["path"].endswith(".gradle"):
                    # Extract dependencies section
                    dep_sections = re.findall(
                        r"dependencies\s*{([^}]*)}", content, re.DOTALL
                    )

                    for section in dep_sections:
                        # Format: implementation 'group:name:version'
                        std_deps = re.findall(
                            r'(\w+)\s*[\(\'"]([^\'"]*):([^\'"]*):([^\'"]*)[\'"\)]',
                            section,
                        )
                        for config, group, name, version in std_deps:
                            dependencies.append(f"{config} '{group}:{name}:{version}'")

                        # Format: implementation(group: 'org.example', name: 'lib', version: '1.0')
                        map_deps = re.findall(
                            r'(\w+)\s*\(\s*group\s*:\s*[\'"]([^\'"]*)[\'"],\s*name\s*:\s*[\'"]([^\'"]*)[\'"],\s*version\s*:\s*[\'"]([^\'"]*)[\'"]',
                            section,
                        )
                        for config, group, name, version in map_deps:
                            dependencies.append(
                                f"{config}(group: '{group}', name: '{name}', version: '{version}')"
                            )

                elif file["path"].endswith("pom.xml"):
                    # Extract Maven dependencies
                    deps = re.findall(
                        r"<dependency>.*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?<version>(.*?)</version>.*?</dependency>",
                        content,
                        re.DOTALL,
                    )

                    for group_id, artifact_id, version in deps:
                        dependencies.append(
                            f"{group_id.strip()}:{artifact_id.strip()}:{version.strip()}"
                        )

            except Exception as e:
                self.logger.warning(
                    f"Error extracting dependencies from {file['path']}: {str(e)}"
                )

        return dependencies

    def _detect_build_system(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect the build system used in the repository focusing on Gradle.

        Args:
            files_info: List of file information dictionaries

        Returns:
            Dictionary with build system information
        """
        build_system = {
            "type": "unknown",
            "has_wrapper": False,
            "files": [],
            "plugins": [],
            "tasks": {},
            "commands": {},
            "shell_scripts": [],  # New field to track shell scripts at root level
        }

        gradlew_file = self.config.target_repo / "gradlew"

        # Find root shell scripts first (outside of hobo directory)
        for file_info in files_info:
            file_path = file_info["path"]

            # Only process shell scripts at the root level
            if (
                file_path.endswith(".sh")
                and "/" not in file_path
                and "\\" not in file_path
            ):
                build_system["shell_scripts"].append(file_path)

                # Add common scripts to commands based on name pattern
                name = file_path.lower()
                if "start" in name:
                    if "run" not in build_system["commands"]:
                        build_system["commands"]["run"] = []
                    build_system["commands"]["run"].append(f"./{file_path}")
                elif "stop" in name:
                    if "stop" not in build_system["commands"]:
                        build_system["commands"]["stop"] = []
                    build_system["commands"]["stop"].append(f"./{file_path}")
                elif "run" in name:
                    if "run" not in build_system["commands"]:
                        build_system["commands"]["run"] = []
                    build_system["commands"]["run"].append(f"./{file_path}")

        for file_info in files_info:
            file_path = file_info["path"]

            # Check for Gradle files
            if file_path.endswith(".gradle"):
                build_system["type"] = "gradle"
                build_system["files"].append(file_path)

                # Analyze the gradle file content
                content = file_info.get("content", "")
                if content:
                    # Extract plugins
                    plugins = re.findall(
                        r'plugins\s*{[^}]*id\s*[\'"]([^\'"]+)[\'"]', content
                    )
                    build_system["plugins"].extend(plugins)

        # Check for Gradle wrapper
        if gradlew_file.exists():
            build_system["has_wrapper"] = True

        return build_system

    def _detect_hobo_configuration(self, target_repo: Path) -> Dict[str, Any]:
        """Detect Hobo deployment configuration in the repository.

        Args:
            target_repo: Path to the repository root

        Returns:
            Dictionary with Hobo configuration information
        """
        hobo_config = {
            "enabled": False,
            "directories": [],
            "has_dockerfile": False,
            "has_docker_compose": False,
            "files": [],
            "services": [],
            "commands": {"start": [], "stop": []},
            "shell_scripts": [],
            "run_scripts": [],
            "auxiliary_scripts": [],
        }

        # Check if hobo directory exists
        hobo_dir = target_repo / "hobo"
        if not hobo_dir.exists() or not hobo_dir.is_dir():
            return hobo_config

        hobo_config["enabled"] = True
        self.logger.debug("Hobo configuration detected")

        # Find all subdirectories in hobo
        for item in hobo_dir.iterdir():
            if item.is_dir():
                hobo_config["directories"].append(item.name)

                # Check for Dockerfile or docker-compose.yml in each subdirectory
                dockerfile = item / "Dockerfile"
                docker_compose = item / "docker-compose.yml"
                run_script = item / "run.sh"

                if dockerfile.exists():
                    hobo_config["has_dockerfile"] = True
                    rel_path = str(dockerfile.relative_to(target_repo))
                    hobo_config["files"].append(rel_path)

                if docker_compose.exists():
                    hobo_config["has_docker_compose"] = True
                    rel_path = str(docker_compose.relative_to(target_repo))
                    hobo_config["files"].append(rel_path)

                    # Analyze docker-compose.yml
                    try:
                        with open(
                            docker_compose, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                        # Try to parse YAML
                        try:
                            compose_data = yaml.safe_load(content)

                            if compose_data and "services" in compose_data:
                                service_names = list(compose_data["services"].keys())
                                hobo_config["services"].extend(service_names)
                        except:
                            # If yaml parsing fails, try with regex
                            services = re.findall(
                                r"^\s*(\w+):\s*$", content, re.MULTILINE
                            )
                            if services:
                                hobo_config["services"].extend(services)

                    except Exception as e:
                        self.logger.warning(
                            f"Error analyzing docker-compose file {docker_compose}: {str(e)}"
                        )

                # Add run.sh to shell scripts within hobo directory
                if run_script.exists():
                    rel_path = str(run_script.relative_to(target_repo))
                    hobo_config["shell_scripts"].append(rel_path)
                    hobo_config["run_scripts"].append(rel_path)
                    hobo_config["files"].append(rel_path)

                # Add other .sh files within this hobo subdirectory
                for sh_file in item.glob("*.sh"):
                    if sh_file != run_script:  # Skip run.sh as we already added it
                        rel_path = str(sh_file.relative_to(target_repo))
                        hobo_config["shell_scripts"].append(rel_path)
                        hobo_config["auxiliary_scripts"].append(rel_path)
                        hobo_config["files"].append(rel_path)

        # Also check for docker-compose.yml directly in hobo directory
        docker_compose = hobo_dir / "docker-compose.yml"
        if docker_compose.exists():
            hobo_config["has_docker_compose"] = True
            rel_path = str(docker_compose.relative_to(target_repo))
            hobo_config["files"].append(rel_path)

        # Find all shell scripts within the hobo directory (not just subdirectories)
        for sh_file in hobo_dir.glob("*.sh"):
            rel_path = str(sh_file.relative_to(target_repo))
            if rel_path not in hobo_config["shell_scripts"]:
                hobo_config["shell_scripts"].append(rel_path)
                hobo_config["run_scripts"].append(rel_path)
                hobo_config["files"].append(rel_path)

        # For any hobo shell scripts that have "start" in their name, add to start commands
        # and for any that have "stop" in their name, add to stop commands
        for script in hobo_config["shell_scripts"]:
            script_name = Path(script).name.lower()
            if "start" in script_name:
                hobo_config["commands"]["start"].append(f"./{script}")
            elif "stop" in script_name:
                hobo_config["commands"]["stop"].append(f"./{script}")

        # For any run scripts in hobo, add to start commands if not already added
        for script in hobo_config["run_scripts"]:
            script_cmd = f"./{script}"
            if (
                script_cmd not in hobo_config["commands"]["start"]
                and "stop" not in Path(script).name.lower()
            ):
                hobo_config["commands"]["start"].append(script_cmd)

        return hobo_config

    def _find_files_by_pattern(self, directory: Path, pattern: str) -> List[Path]:
        """Helper to find files matching a pattern in a directory.

        Args:
            directory: Directory to search in
            pattern: Pattern to match

        Returns:
            List of paths matching the pattern
        """
        result = []
        for root, _, files in os.walk(directory):
            for file in files:
                if pattern in file:
                    result.append(Path(os.path.join(root, file)))
        return result

    def _detect_custom_tools(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect custom tools used in the repository with focus on Java/Gradle tools.

        Args:
            files_info: List of file information dictionaries

        Returns:
            Dictionary with custom tools information
        """
        custom_tools = []

        # Check for common custom tools and directories
        custom_tool_indicators = {
            "docker": ["Dockerfile", "docker-compose.yml"],
            "spring-boot": ["application.properties", "application.yml"],
            "lombok": ["lombok.config"],
        }

        for file_info in files_info:
            file_path = file_info["path"]
            file_name = os.path.basename(file_path)
            content = file_info.get("content", "")

            for tool, indicators in custom_tool_indicators.items():
                if (
                    file_name in indicators
                    or any(file_path.endswith(ext) for ext in indicators)
                    or any(part in file_path for part in indicators)
                ):
                    if tool not in custom_tools:
                        custom_tools.append(tool)

            # Check for Spring Boot in Java files
            if (
                file_path.endswith(".java")
                and content
                and "@SpringBootApplication" in content
            ):
                if "spring-boot" not in custom_tools:
                    custom_tools.append("spring-boot")

            # Check for Hobo
            if "hobo" in file_path:
                if "hobo" not in custom_tools:
                    custom_tools.append("hobo")

            # Check for Gradle plugins
            if file_path.endswith(".gradle") and content:
                # Look for specific plugins
                if (
                    "org.springframework.boot" in content
                    and "spring-boot" not in custom_tools
                ):
                    custom_tools.append("spring-boot")

                if "lombok" in content and "lombok" not in custom_tools:
                    custom_tools.append("lombok")

        return {"custom_tools": custom_tools}

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

        # Add build commands if available
        build_system = info.get("build_system", {})
        if build_system and build_system.get("commands"):
            result.append("\n## Build Commands")
            for cmd_name, cmd in build_system.get("commands", {}).items():
                result.append(f"- {cmd_name}: `{cmd}`")

        # Add Hobo commands if available
        hobo_config = info.get("hobo_config", {})
        if hobo_config and hobo_config.get("enabled"):
            result.append("\n## Hobo Commands")
            for cmd_name, cmds in hobo_config.get("commands", {}).items():
                if cmds:
                    result.append(f"- {cmd_name}: `{cmds[0]}`")

        # Add dependencies (limit to top 20)
        if info.get("dependencies"):
            result.append("\n## Dependencies")
            # Limit to top 20 dependencies to avoid overwhelming
            for dep in info["dependencies"][:20]:
                result.append(f"- {dep}")
            if len(info["dependencies"]) > 20:
                result.append(f"- ... and {len(info['dependencies']) - 20} more")

        return "\n".join(result)
