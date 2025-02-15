from pathlib import Path
import os
import json

from dotenv import load_dotenv
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools.render import render_text_description

from file_info import FileInfo
from repo_analyzer_tools import RepoAnalyzerTools
from repo_info import RepoInfo


class RepoAnalyzerAgent:
    """Main agent class for repository analysis"""

    # Define the file types we want to analyze
    ANALYZABLE_EXTENSIONS = {
        # Java ecosystem
        '.java',
        '.groovy',
        '.scala',
        # Python ecosystem
        '.py',
        # Node.js ecosystem
        '.js',
        '.jsx',
        '.ts',
        '.tsx'
    }

    def __init__(self, temperature: float = 0):
        load_dotenv()
        self.tools = [
            RepoAnalyzerTools.detect_language,
            RepoAnalyzerTools.generate_readme,
            RepoAnalyzerTools.summarize_code,
        ]
        self.llm = ChatOpenAI(temperature=temperature, model_name="gpt-4o-mini")
        self._setup_agent()
        self.file_summaries = []  # Store summaries of analyzed files

    def _setup_agent(self):
        """Sets up the agent with tools and prompt template"""
        template = """
        You are an expert repository analyzer specializing in Java, Python, and Node.js codebases. 
        Your task is to analyze a code repository and generate comprehensive documentation. 

        For Java repositories:
        - Look for Spring Boot annotations and configurations
        - Identify Maven/Gradle build files
        - Check for main application classes
        - Analyze package structure

        You have access to these tools:

        {tools}

        Use this format:

        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action (must be a valid JSON string)
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question

        Begin!

        Question: {input}
        Thought: {agent_scratchpad}
        """

        self.prompt = PromptTemplate.from_template(template=template).partial(
            tools=render_text_description(self.tools),
            tool_names=", ".join([t.name for t in self.tools]),
        )

        self.agent = (
                {
                    "input": lambda x: x["input"],
                    "agent_scratchpad": lambda x: format_log_to_str(x["agent_scratchpad"]),
                }
                | self.prompt
                | self.llm
                | ReActSingleInputOutputParser()
        )

    def analyze_repository(self, repo_path: str) -> str:
        """
        Analyzes a repository and generates a README.md file if one doesn't exist
        or is empty.

        Args:
            repo_path: Path to the repository root directory

        Returns:
            str: Generated README.md content or message if README exists
        """
        # Check for existing README.md
        readme_path = os.path.join(repo_path, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return "README.md already exists and is not empty. Skipping analysis."

        try:
            repo_info = self._gather_repo_info(repo_path)

            # First pass: Analyze all files and collect summaries
            for file_info in repo_info.files:
                summary = RepoAnalyzerTools.summarize_code(json.dumps({
                    "path": file_info.path,
                    "content": file_info.content,
                    "language": file_info.language
                }))
                self.file_summaries.append({
                    "path": file_info.path,
                    "summary": summary
                })

            # Add file summaries to repo_info
            repo_info_dict = repo_info.dict()
            repo_info_dict["file_summaries"] = self.file_summaries

            # Create a prompt for README generation using the collected information
            summaries = "\n".join([
                f"- {summary['path']}: {summary['summary']}"
                for summary in repo_info_dict['file_summaries']
            ])

            prompt = f"""You are a technical documentation expert. Create a comprehensive README.md file for a {repo_info_dict['primary_language']} project.

Project Name: {repo_info_dict['name']}

Here are the analyzed files and their summaries:
{summaries}

The repository has the following entry points: {', '.join(repo_info_dict['entry_points'])}

Generate a professional README.md that includes:
1. Project title and description (based on the code analysis)
2. Main features and functionality
3. Project structure highlighting key components
4. Setup/installation instructions
5. Basic usage examples
6. Dependencies (if identifiable from the code)

Use proper Markdown formatting. Keep it professional, clear, and concise."""

            try:
                readme_content = self.llm.invoke(prompt).content
                self._save_readme(repo_path, readme_content)
                return readme_content
            except Exception as e:
                return f"Failed to generate README.md: {str(e)}"

        except Exception as e:
            print(f"Error in analyze_repository: {str(e)}")
            return f"Failed to generate README.md: {str(e)}"

    def _gather_repo_info(self, repo_path: str) -> RepoInfo:
        """Gathers information about the repository"""
        repo_info = RepoInfo(
            name=Path(repo_path).name,
            primary_language="Unknown",
            files=[],
            config_files=[],
            entry_points=[],
        )

        for root, _, files in os.walk(repo_path):
            # Skip common build and dependency directories
            if any(part in root for part in [".git", "node_modules", "target", "build"]):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)

                # Skip files that aren't in our analyzable extensions
                if not any(rel_path.endswith(ext) for ext in self.ANALYZABLE_EXTENSIONS):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    language = RepoAnalyzerTools.detect_language(rel_path)

                    file_info = FileInfo(
                        path=rel_path,
                        content=content,
                        language=language,
                        is_entry_point=self._is_entry_point(content, language)
                    )

                    repo_info.files.append(file_info)

                    if file_info.is_entry_point:
                        repo_info.entry_points.append(rel_path)

                except Exception as e:
                    print(f"Error processing {rel_path}: {str(e)}")

        # Determine primary language
        if repo_info.files:
            lang_count = {}
            for file in repo_info.files:
                if file.language != "Unknown":
                    lang_count[file.language] = lang_count.get(file.language, 0) + 1
            if lang_count:
                repo_info.primary_language = max(lang_count.items(), key=lambda x: x[1])[0]

        return repo_info

    def _is_entry_point(self, content: str, language: str) -> bool:
        """Determines if a file is an entry point based on its content and language"""
        entry_point_patterns = {
            "Python": ['if __name__ == "__main__"'],
            "Java": ['public static void main', '@SpringBootApplication'],
            "JavaScript": ['export default', 'module.exports'],
            "TypeScript": ['export default', 'export const']
        }

        patterns = entry_point_patterns.get(language, [])
        return any(pattern in content for pattern in patterns)

    def _save_readme(self, repo_path: str, content: str):
        """Saves the README.md file"""
        readme_path = os.path.join(repo_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)