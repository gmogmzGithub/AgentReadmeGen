from typing import Dict, Any
from pathlib import Path
import json
from langchain.agents import tool
from langchain_openai import ChatOpenAI


class RepoAnalyzerTools:
    """Collection of tools for repository analysis"""

    @staticmethod
    @tool("summarize_code")
    def summarize_code(file_info: str) -> str:
        """
        Uses LLM to analyze code content and provide a summary of its functionality.
        Input should be a JSON string with 'path', 'content', and 'language' keys.
        """
        if isinstance(file_info, str):
            try:
                file_info = json.loads(file_info)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input"
        try:
            llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

            prompt = f"""Analyze the following {file_info['language']} code and provide a concise summary of its main functionality, purpose, and any key components or features. Focus on what the code does rather than implementation details.

Code from {file_info['path']}:

{file_info['content']}

Provide a summary in 2-3 sentences maximum."""

            response = llm.invoke(prompt)
            return response.content

        except Exception as e:
            return f"Error analyzing code: {str(e)}"

    @staticmethod
    @tool
    def detect_language(file_path: str) -> str:
        """
        Detects the programming language based on file extension.
        """
        ext_map = {
            ".py": "Python",
            ".java": "Java",
            ".groovy": "Groovy",
            ".scala": "Scala",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript"
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")

    @staticmethod
    @tool
    def generate_readme(repo_info: Dict[str, Any]) -> str:
        """
        Generates README.md content based on repository analysis.
        Input should be a dictionary containing repository information including file summaries.
        """
        try:
            llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

            # Extract summaries
            summaries = "\n".join([
                f"- {summary['path']}: {summary['summary']}"
                for summary in repo_info.get('file_summaries', [])
            ])

            prompt = f"""Create a comprehensive README.md file for a {repo_info['primary_language']} project. 
            Here are the analyzed files and their summaries:

            {summaries}

            The README should include:
            1. Project title (use the repository name: {repo_info['name']})
            2. A clear description of the project's purpose based on the code analysis
            3. Main features and functionality
            4. Project structure highlighting key components
            5. Setup/installation instructions appropriate for a {repo_info['primary_language']} project
            6. Basic usage examples if entry points were found

            Format the README using proper Markdown syntax. Keep it professional and concise."""

            response = llm.invoke(prompt)
            return response.content

        except Exception as e:
            return f"Error generating README: {str(e)}"
