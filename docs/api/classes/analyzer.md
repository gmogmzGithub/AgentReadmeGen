## Overview
Performs deep analysis of code repositories. It examines file structures, identifies languages, analyzes dependencies, detects build systems, and provides comprehensive insights about the codebase.

## Key Components

### RepositoryAnalyzer Class
```python
class RepositoryAnalyzer:
    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.llm = ChatOpenAI(model=config.model, temperature=0)
        self.code_analyzer = CodeUnderstandingAnalyzer(self.llm)
        self.repo_info = {}
        self.analyzed = False
```

### Supported File Types
The analyzer recognizes multiple ecosystems:

```python
ANALYZABLE_EXTENSIONS = {
    # Java
    ".java", ".groovy", ".scala", ".gradle",
    # Python
    ".py", ".toml", ".cfg", ".ini",
    # JavaScript/TypeScript 
    ".js", ".jsx", ".ts", ".tsx", ".json",
    # Web
    ".html", ".css", ".scss",
    # Documentation
    ".md", ".rst", ".txt",
    # Configuration
    ".yaml", ".yml", ".xml", ".env"
}
```

### Key Project Files
Automatically detects and analyzes important project files:
```python
KEY_PROJECT_FILES = {
    # General
    "README.md", "LICENSE", "CONTRIBUTING.md",
    # Package managers
    "package.json", "Pipfile", "requirements.txt",
    # Configuration
    "Dockerfile", "docker-compose.yml",
    ".env.example", ".nvmrc"
}
```

## Analysis Process

### 1. File Discovery and Analysis
```python
def _gather_file_info(self) -> Dict[str, Any]:
    """Gather information about files in the repository."""
    files_info = []
    
    # First pass: Key project files
    for file_name in self.KEY_PROJECT_FILES:
        # Process important files regardless of extension
        
    # Second pass: Regular file discovery
    for root, _, files in os.walk(self.config.target_repo):
        # Skip common directories to ignore
        # Process files based on extensions
```

### 2. Language Detection
```python
def _detect_language(self, file_path: str) -> str:
    """Detect programming language based on file extension."""
    ext_map = {
        ".py": "Python",
        ".java": "Java",
        ".js": "JavaScript",
        # ... more mappings
    }
```

### 3. Entry Point Detection
```python
def _is_entry_point(self, content: str, language: str, file_path: str) -> bool:
    """Determine if a file is an entry point."""
    patterns = {
        "Python": ['if __name__ == "__main__":', "def main("],
        "Java": ["public static void main", "@SpringBootApplication"],
        "JavaScript": ["export default ", "module.exports"]
    }
```

### 4. Dependency Analysis
```python
def _find_dependencies(self, files_info: List[Dict[str, Any]]) -> List[str]:
    """Find dependencies from configuration files."""
    # Extract from:
    # - pyproject.toml/Pipfile (Python)
    # - package.json (Node.js)
    # - requirements.txt (Python)
```

### 5. Build System Detection
```python
def _detect_build_system(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect the build system used."""
    build_system_indicators = {
        "gradle": [".gradle", "build.gradle"],
        "maven": ["pom.xml", "mvnw"],
        "npm": ["package.json", "yarn.lock"]
    }
```

## Integration Points

### With config.py
- Receives configuration through constructor
- Uses config for file paths and settings
```python
def __init__(self, config: GeneratorConfig) -> None:
    self.config = config
    self.llm = ChatOpenAI(model=config.model, temperature=0)
```

### With code_understanding_analyzer.py
- Delegates deep code analysis
```python
code_understanding = self.code_analyzer.analyze_code_understanding(
    files_info, self.config.target_repo
)
```

### With readme_generator.py
- Provides repository analysis results
- Supports incremental analysis
```python
def analyze_repository(self, update: bool = True) -> str:
    """Analyze repository structure and content."""
```

## Key Features

### 1. Smart README Detection
- Checks for existing READMEs
- 
### 2. File Size Management
```python
MAX_FILE_SIZE = 1024 * 100  # 100KB max file size
```

### 3. Comprehensive Analysis
- Programming languages used
- File distribution
- Entry points
- Dependencies
- Build systems
- Custom tools

### 4. Repository Structure Analysis
```python
def _detect_custom_tools(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect custom tools used in the repository."""
    custom_tool_indicators = {
        "docker": ["Dockerfile", "docker-compose.yml"],
        "kubernetes": [".k8s", "kubernetes"],
        "terraform": [".tf", "terraform"]
    }
```

## Output Format
The analyzer produces structured information:
```python
{
    "name": repository_name,
    "primary_language": detected_language,
    "total_files": count,
    "entry_points": [...],
    "config_files": [...],
    "dependencies": [...],
    "build_system": {...},
    "custom_tools": {...},
    "code_understanding": "...",
    "file_breakdown": {...}
}
```