import sys

from dotenv import load_dotenv
from pathlib import Path
from repo_analyzer_agent import RepoAnalyzerAgent

load_dotenv()

if __name__ == "__main__":
    # Set the specific repository path
    repo_path = "/Users/gmogmz/Indeed/repos/java-ecosystem-team/nop-canary"

    # Add path validation
    path = Path(repo_path)
    if not path.exists():
        print(f"Error: Path does not exist: {repo_path}")
        sys.exit(1)
    if not path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}")
        sys.exit(1)

    print(f"Analyzing repository at: {repo_path}")
    agent = RepoAnalyzerAgent()
    readme_content = agent.analyze_repository(repo_path)
    print("\nGenerated README.md content:")
    print(readme_content)
