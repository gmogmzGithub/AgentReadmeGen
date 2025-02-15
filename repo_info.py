from typing import List
from pydantic import BaseModel, Field

from file_info import FileInfo


class RepoInfo(BaseModel):
    """Schema for repository information"""

    name: str = Field(description="Name of the repository")
    primary_language: str = Field(description="Primary programming language")
    files: List[FileInfo] = Field(description="List of analyzed files")
    config_files: List[str] = Field(description="List of configuration files found")
    entry_points: List[str] = Field(description="List of entry point files")
