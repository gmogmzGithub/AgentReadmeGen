"""Repository analyzers package."""

from src.analyzers.java_analizer import JavaAnalyzer
from src.analyzers.python_analizer import PythonAnalyzer
from src.analyzers.javascript_analizer import JavaScriptAnalyzer


def get_analyzer_for_repo(config):
    """Get the appropriate analyzer for a repository.

    Args:
        config: Generator configuration

    Returns:
        Appropriate analyzer instance for the repository
    """
    # If language is explicitly specified, use that analyzer
    if config.language != "auto":
        if config.language == "java":
            return JavaAnalyzer(config)
        elif config.language == "python":
            return PythonAnalyzer(config)
        elif config.language == "javascript":
            return JavaScriptAnalyzer(config)

    # Otherwise, auto-detect based on repository contents
    # This simple auto-detection can be expanded later

    # For now, check for key files to determine language
    repo_path = config.target_repo

    # Check for Java/Gradle
    java_indicators = [
        repo_path / "build.gradle",
        repo_path / "gradlew",
        repo_path / "pom.xml",
        repo_path / "src" / "main" / "java",
    ]

    for indicator in java_indicators:
        if indicator.exists():
            return JavaAnalyzer(config)

    # Check for Python
    python_indicators = [
        repo_path / "requirements.txt",
        repo_path / "setup.py",
        repo_path / "pyproject.toml",
        repo_path / "Pipfile",
    ]

    for indicator in python_indicators:
        if indicator.exists():
            return PythonAnalyzer(config)

    # Check for JavaScript
    js_indicators = [
        repo_path / "package.json",
        repo_path / "node_modules",
        repo_path / "webpack.config.js",
        repo_path / "tsconfig.json",
    ]

    for indicator in js_indicators:
        if indicator.exists():
            return JavaScriptAnalyzer(config)

    # Default to Java analyzer for now
    return JavaAnalyzer(config)
