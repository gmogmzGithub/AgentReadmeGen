from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Schema for file information"""

    path: str = Field(description="Path to the file")
    content: str = Field(description="Content of the file")
    language: str = Field(description="Programming language of the file")
    is_entry_point: bool = Field(description="Whether this file is an entry point")
