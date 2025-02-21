# code_understanding_analyzer.py

## Overview
Provides advanced code analysis capabilities using Abstract Syntax Tree (AST) parsing and pattern matching. It analyzes code structure, relationships between components, and generates an understanding of codebases across multiple programming languages.

## Key Components

### CodeUnderstandingAnalyzer Class
```python
class CodeUnderstandingAnalyzer:
    def __init__(self, llm, max_tokens=5000):
        self.llm = llm
        self.max_tokens = max_tokens
        self.code_understanding_prompt = PromptTemplate.from_template("""
            Analyze the following code samples...
        """)
```

## Analysis Strategies

### 1. Python AST Analysis
```python
def _extract_ast_info(self, file_path: str, content: str, language: str) -> Dict:
    """Extract AST information from Python code content."""
    try:
        tree = ast.parse(content)
        
        functions = []  # Store function definitions
        classes = []    # Store class definitions
        imports = []    # Store import statements
        
        for node in ast.walk(tree):
            # Extract functions
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                docstring = ast.get_docstring(node) or ""
                functions.append({
                    "name": node.name,
                    "args": args,
                    "docstring": docstring,
                    "line": node.lineno,
                })
                
            # Extract classes
            elif isinstance(node, ast.ClassDef):
                bases = [base.id for base in node.bases if hasattr(base, "id")]
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                docstring = ast.get_docstring(node) or ""
                classes.append({
                    "name": node.name,
                    "bases": bases,
                    "methods": methods,
                    "docstring": docstring,
                    "line": node.lineno,
                })
                
            # Extract imports
            elif isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
```

### 2. JavaScript/TypeScript Analysis
```python
def _extract_js_info(self, content: str) -> Dict:
    """Extract information from JavaScript/TypeScript files."""
    functions = []
    classes = []
    imports = []
    
    # Function detection
    function_pattern = r"(?:function|const|let|var)\s+(\w+)\s*\([^)]*\)"
    
    # Class detection
    class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
    
    # Import detection
    import_pattern = r'import\s+(?:{[^}]*}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
```

### 3. Generic Language Analysis
```python
def _extract_code_info(self, file_path: str, content: str, language: str) -> Dict:
    """Extract code information based on language."""
    if language == "Python":
        return self._extract_ast_info(file_path, content, language)
    elif language in ["JavaScript", "TypeScript"]:
        return self._extract_js_info(content)
    else:
        # Pattern matching for other languages
        function_patterns = {
            "Java": r"(?:public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)",
            "Go": r"func\s+(\w+)\s*\([^)]*\)",
            "Ruby": r"def\s+(\w+)",
            "PHP": r"function\s+(\w+)\s*\([^)]*\)"
        }
```

## Relationship Analysis

### Method Relationships
```python
def find_method_relationships(self, code_infos: Dict[str, Dict]) -> List[str]:
    """Find relationships between methods and classes across files."""
    relationships = []
    all_classes = {}
    all_functions = {}
    imports_by_file = {}
    
    # First pass: collect all classes and functions
    for file_path, info in code_infos.items():
        # Collect class information
        for cls in info.get("classes", []):
            all_classes[cls["name"]] = {
                "file": file_path,
                "methods": cls.get("methods", []),
                "bases": cls.get("bases", []),
            }
            
        # Collect function information
        for func in info.get("functions", []):
            if func["name"] not in all_functions:
                all_functions[func["name"]] = []
            all_functions[func["name"]].append({
                "file": file_path,
                "args": func.get("args", []),
            })
```

### Types of Relationships Detected

1. **Inheritance**
```python
# Class inheritance detection
for cls in info.get("classes", []):
    for base in cls.get("bases", []):
        if base in all_classes:
            relationships.append(
                f"Class '{cls['name']}' in {file_path} inherits from '{base}'"
            )
```

2. **Function References**
```python
# Function usage detection
content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
for func_name, occurrences in all_functions.items():
    if func_name in content:
        for occurrence in occurrences:
            if occurrence["file"] != file_path:
                relationships.append(
                    f"Function '{func_name}' from {occurrence['file']} is referenced"
                )
```

## Code Understanding Generation

### Analysis Process
```python
def analyze_code_understanding(self, file_infos: List[Dict], repo_path: Path) -> str:
    """Analyze code to understand its functionality and relationships."""
    key_files = []
    entry_points = []
    code_infos = {}
    
    # Identify key files
    for file_info in file_infos:
        if file_info.get("is_entry_point", False):
            entry_points.append(file_info)
            key_files.append(file_info)
        elif file_info.get("is_key_file", False):
            key_files.append(file_info)
```

### Token Management
```python
# Very rough token estimation (assuming average 5 chars per token)
estimated_tokens = len(content) // 5
if token_count + estimated_tokens > self.max_tokens:
    # Skip if adding this file would exceed token limit
    continue
```

## Integration Points

### With RepositoryAnalyzer
```python
# In RepositoryAnalyzer
self.code_analyzer = CodeUnderstandingAnalyzer(self.llm)
code_understanding = self.code_analyzer.analyze_code_understanding(
    files_info, self.config.target_repo
)
```

### With LangChain
```python
response = self.llm.invoke(
    self.code_understanding_prompt.format(
        code_samples=code_samples_text,
        method_relationships=method_relationships_text,
    )
)
```