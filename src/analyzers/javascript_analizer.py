"""JavaScript repository analysis module (placeholder for future implementation)."""

from pathlib import Path
from typing import Dict, List, Any, Set

from src.analyzers.base_analizer import BaseAnalyzer


class JavaScriptAnalyzer(BaseAnalyzer):
    """Analyzes JavaScript/TypeScript repository structure and content."""

    def _get_analyzable_extensions(self) -> set:
        """Get file extensions that should be analyzed for JavaScript projects."""
        return {
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".json",
            ".html",
            ".css",
            ".scss",
            ".vue",
        }

    def _get_language_specific_key_files(self) -> set:
        """Get JavaScript-specific key files to always include."""
        return {
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "tsconfig.json",
            "webpack.config.js",
            "babel.config.js",
            "vite.config.js",
            "next.config.js",
            ".eslintrc",
            "index.js",
            "main.js",
            "app.js",
        }

    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language based on file extension for JavaScript projects."""
        ext_map = {
            ".js": "JavaScript",
            ".jsx": "React",
            ".ts": "TypeScript",
            ".tsx": "React TypeScript",
            ".json": "JSON",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".vue": "Vue",
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")

    def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
        """Determine if a file is an entry point for JavaScript projects."""
        # This is a placeholder implementation
        # Will be implemented in future versions
        return False

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

        # Get shell scripts information from file_data
        root_shell_scripts = []
        hobo_shell_scripts = []
        all_shell_scripts = []

        for f in files_info:
            if f["path"].endswith(".sh"):
                all_shell_scripts.append(f["path"])

                # Check if it's in the root directory
                if "/" not in f["path"] and "\\" not in f["path"]:
                    root_shell_scripts.append(f["path"])
                # Check if it's in the hobo directory
                elif f["path"].startswith("hobo/") or f["path"].startswith("hobo\\"):
                    hobo_shell_scripts.append(f["path"])

        build_system = self._detect_build_system(files_info)
        hobo_config = self._detect_hobo_configuration(self.config.target_repo)
        dependencies = self._find_dependencies(files_info)
        custom_tools = self._detect_custom_tools(files_info)

        # Make sure build_system has the root shell scripts
        build_system["shell_scripts"] = root_shell_scripts

        # Make sure hobo_config only has hobo shell scripts
        hobo_config["shell_scripts"] = hobo_shell_scripts

        # Ensure we only have hobo scripts in hobo_config.commands
        if hobo_config.get("enabled"):
            for cmd_type in ["start", "stop"]:
                filtered_cmds = []
                for cmd in hobo_config["commands"].get(cmd_type, []):
                    # Extract script path from command
                    script_path = cmd[2:] if cmd.startswith("./") else cmd
                    # Only keep if it's a hobo script
                    if script_path in hobo_shell_scripts or "hobo" in script_path:
                        filtered_cmds.append(cmd)
                hobo_config["commands"][cmd_type] = filtered_cmds

        return {
            "java_files": java_files,
            "gradle_files": gradle_files,
            "shell_scripts": all_shell_scripts,
            "root_shell_scripts": root_shell_scripts,
            "hobo_shell_scripts": hobo_shell_scripts,
            "build_system": build_system,
            "hobo_config": hobo_config,
            "dependencies": dependencies,
            "custom_tools": custom_tools,
        }

    def _generate_analysis_text(self) -> None:
        """Generate analysis text from repository information."""
        # This is a placeholder implementation
        # Will be implemented in future versions
        self.repo_info[
            "analysis"
        ] = "JavaScript repository analysis not yet implemented."

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
            for cmd_name, cmd_value in build_system.get("commands", {}).items():
                if isinstance(cmd_value, list):
                    # For commands that are lists
                    for cmd in cmd_value:
                        result.append(f"- {cmd_name}: `{cmd}`")
                else:
                    # For commands that are strings
                    result.append(f"- {cmd_name}: `{cmd_value}`")

        # Add root shell scripts
        root_shell_scripts = build_system.get("shell_scripts", [])
        if root_shell_scripts:
            result.append("\n## Root Shell Scripts")
            for script in root_shell_scripts:
                result.append(f"- {script}")

        # Add Hobo commands if available
        hobo_config = info.get("hobo_config", {})
        if hobo_config and hobo_config.get("enabled"):
            result.append("\n## Hobo Configuration")

            if hobo_config.get("has_dockerfile"):
                result.append("- Uses Dockerfile")
            if hobo_config.get("has_docker_compose"):
                result.append("- Uses docker-compose")

            # Add Hobo commands
            if hobo_config.get("commands"):
                result.append("\n### Hobo Commands")
                for cmd_name, cmds in hobo_config.get("commands", {}).items():
                    if cmds:
                        for cmd in cmds:
                            result.append(f"- {cmd_name}: `{cmd}`")

            # Add Hobo shell scripts
            hobo_shell_scripts = hobo_config.get("shell_scripts", [])
            if hobo_shell_scripts:
                result.append("\n### Hobo Shell Scripts")
                for script in hobo_shell_scripts:
                    result.append(f"- {script}")

        # Add dependencies (limit to top 20)
        if info.get("dependencies"):
            result.append("\n## Dependencies")
            # Limit to top 20 dependencies to avoid overwhelming
            for dep in info["dependencies"][:20]:
                result.append(f"- {dep}")
            if len(info["dependencies"]) > 20:
                result.append(f"- ... and {len(info['dependencies']) - 20} more")

        return "\n".join(result)
