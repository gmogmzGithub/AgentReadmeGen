"""Enhanced repository analysis module with code understanding."""

import os
import logging
import re
from pathlib import Path
from typing import Dict, List
import ast

from langchain_core.prompts import PromptTemplate


class CodeUnderstandingAnalyzer:
    """Provides advanced code understanding capabilities."""

    def __init__(self, llm, max_tokens=5000):
        """Initialize the code understanding analyzer.

        Args:
            llm: Language model for analysis
            max_tokens: Maximum tokens to include in LLM context
        """
        self.llm = llm
        self.max_tokens = max_tokens
        self.code_understanding_prompt = PromptTemplate.from_template(
            """Analyze the following code samples to understand their purpose and relationships.

            # Code Samples

            {code_samples}

            # Method Relationships

            {method_relationships}

            Based on these code samples, provide a comprehensive analysis of:
            1. The primary purpose of this codebase
            2. Key functionality and features
            3. How the components work together
            4. The overall architecture and design patterns used
            5. How the code is meant to be used (based on entry points and public APIs)

            Be specific and detailed, focusing on what the code actually does rather than just its structure.
            """
        )

    def _extract_ast_info(self, file_path: str, content: str, language: str) -> Dict:
        """Extract AST information from code content."""
        if language != "Python":
            return {"functions": [], "classes": [], "imports": []}

        try:
            tree = ast.parse(content)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                # Get function definitions
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    docstring = ast.get_docstring(node) or ""
                    functions.append(
                        {
                            "name": node.name,
                            "args": args,
                            "docstring": docstring,
                            "line": node.lineno,
                        }
                    )

                # Get class definitions
                elif isinstance(node, ast.ClassDef):
                    bases = [base.id for base in node.bases if hasattr(base, "id")]
                    methods = [
                        m.name for m in node.body if isinstance(m, ast.FunctionDef)
                    ]
                    docstring = ast.get_docstring(node) or ""
                    classes.append(
                        {
                            "name": node.name,
                            "bases": bases,
                            "methods": methods,
                            "docstring": docstring,
                            "line": node.lineno,
                        }
                    )

                # Get imports
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")

            return {"functions": functions, "classes": classes, "imports": imports}
        except SyntaxError:
            logging.warning(f"Could not parse {file_path} as Python")
            return {"functions": [], "classes": [], "imports": []}
        except Exception as e:
            logging.warning(f"Error extracting AST from {file_path}: {str(e)}")
            return {"functions": [], "classes": [], "imports": []}

    def _extract_js_info(self, content: str) -> Dict:
        """Extract basic information from JavaScript/TypeScript files."""
        # Simple regex-based extraction for JS/TS
        functions = []
        classes = []
        imports = []

        # Match function declarations
        function_pattern = r"(?:function|const|let|var)\s+(\w+)\s*\([^)]*\)"
        for match in re.finditer(function_pattern, content):
            functions.append({"name": match.group(1)})

        # Match class declarations
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            parent = match.group(2) if match.group(2) else ""
            classes.append({"name": class_name, "parent": parent})

        # Match import statements
        import_pattern = r'import\s+(?:{[^}]*}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))

        return {"functions": functions, "classes": classes, "imports": imports}

    def _extract_code_info(self, file_path: str, content: str, language: str) -> Dict:
        """Extract code information based on language."""
        if language == "Python":
            return self._extract_ast_info(file_path, content, language)
        elif language in ["JavaScript", "TypeScript"]:
            return self._extract_js_info(content)
        else:
            # For other languages, just do basic pattern matching
            functions = []
            classes = []

            # Simple function pattern matching for various languages
            function_patterns = {
                "Java": r"(?:public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)",
                "Go": r"func\s+(\w+)\s*\([^)]*\)",
                "Ruby": r"def\s+(\w+)",
                "PHP": r"function\s+(\w+)\s*\([^)]*\)",
                "default": r"\b(?:function|def|func)\s+(\w+)\b",
            }

            pattern = function_patterns.get(language, function_patterns["default"])
            for match in re.finditer(pattern, content):
                functions.append({"name": match.group(1)})

            # Simple class pattern matching
            class_patterns = {
                "Java": r"class\s+(\w+)(?:\s+extends\s+(\w+))?",
                "Ruby": r"class\s+(\w+)(?:\s+<\s+(\w+))?",
                "PHP": r"class\s+(\w+)(?:\s+extends\s+(\w+))?",
                "default": r"class\s+(\w+)",
            }

            pattern = class_patterns.get(language, class_patterns["default"])
            for match in re.finditer(pattern, content):
                classes.append({"name": match.group(1)})

            return {"functions": functions, "classes": classes, "imports": []}

    def find_method_relationships(self, code_infos: Dict[str, Dict]) -> List[str]:
        """Find relationships between methods and classes across files."""
        relationships = []
        all_classes = {}
        all_functions = {}
        imports_by_file = {}

        # First pass: collect all classes and functions
        for file_path, info in code_infos.items():
            for cls in info.get("classes", []):
                all_classes[cls["name"]] = {
                    "file": file_path,
                    "methods": cls.get("methods", []),
                    "bases": cls.get("bases", []),
                }

            for func in info.get("functions", []):
                if func["name"] not in all_functions:
                    all_functions[func["name"]] = []
                all_functions[func["name"]].append(
                    {
                        "file": file_path,
                        "args": func.get("args", []),
                    }
                )

            imports_by_file[file_path] = info.get("imports", [])

        # Second pass: find relationships
        for file_path, info in code_infos.items():
            file_imports = set(imports_by_file[file_path])

            # Check for inheritance relationships
            for cls in info.get("classes", []):
                for base in cls.get("bases", []):
                    if base in all_classes:
                        relationships.append(
                            f"Class '{cls['name']}' in {file_path} inherits from '{base}' in {all_classes[base]['file']}"
                        )

            # Check for function calls (basic approach - just checking if function names appear)
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            for func_name, occurrences in all_functions.items():
                if func_name in content:
                    for occurrence in occurrences:
                        if occurrence["file"] != file_path:
                            relationships.append(
                                f"Function '{func_name}' from {occurrence['file']} is referenced in {file_path}"
                            )

        # Limit to most important relationships to avoid context overflow
        return relationships[:50] if len(relationships) > 50 else relationships

    # Fix for analyze_code_understanding method in CodeUnderstandingAnalyzer class

    def analyze_code_understanding(
        self, file_infos: List[Dict], repo_path: Path
    ) -> str:
        """Analyze code to understand its functionality and relationships."""
        key_files = []
        entry_points = []
        code_infos = {}

        # Identify key files to analyze
        for file_info in file_infos:
            if file_info.get("is_entry_point", False):
                entry_points.append(file_info)
                key_files.append(file_info)
            elif file_info.get("is_key_file", False):
                key_files.append(file_info)

        # If we don't have enough key files, add some of the largest files
        if len(key_files) < 3:
            remaining = sorted(
                [f for f in file_infos if f not in key_files],
                key=lambda x: x.get("size", 0),
                reverse=True,
            )
            key_files.extend(remaining[: 5 - len(key_files)])

        # Extract code samples and info
        code_samples = []
        token_count = 0
        for file_info in key_files:
            try:
                file_path = os.path.join(repo_path, file_info["path"])
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Very rough token estimation (assuming average 5 chars per token)
                estimated_tokens = len(content) // 5
                if token_count + estimated_tokens > self.max_tokens:
                    # If adding this file would exceed token limit, skip it
                    continue

                token_count += estimated_tokens

                code_sample = f"""
                ## File: {file_info['path']}
                Language: {file_info['language']}
                Entry Point: {'Yes' if file_info.get('is_entry_point', False) else 'No'}

                ```{file_info['language'].lower()}
                {content}
                ```
                """
                code_samples.append(code_sample)

                # Extract code information
                code_info = self._extract_code_info(
                    file_path, content, file_info["language"]
                )
                code_infos[file_info["path"]] = code_info

            except Exception as e:
                logging.warning(f"Error processing {file_info['path']}: {str(e)}")

        # Find method relationships
        method_relationships = self.find_method_relationships(code_infos)
        method_relationships_text = "\n".join(method_relationships)

        # Generate code understanding
        try:
            code_samples_text = "\n\n".join(code_samples)
            response = self.llm.invoke(
                self.code_understanding_prompt.format(
                    code_samples=code_samples_text,
                    method_relationships=method_relationships_text,
                )
            )
            # Extract the content string from the AIMessage object
            return response.content
        except Exception as e:
            logging.error(f"Error in code understanding analysis: {str(e)}")
            return "Could not perform deep code analysis due to an error."
