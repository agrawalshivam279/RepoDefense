import re
import uuid
from datetime import datetime
from typing import Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

GITHUB_URL_REGEX = re.compile(
    r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
)


class ProjectCreate(BaseModel):
    """Schema for registering a new GitHub repository project."""

    github_url: str = Field(
        description="Public or authenticated GitHub repository URL",
        examples=["https://github.com/fastapi/fastapi"],
    )
    name: Union[str, None] = Field(
        default=None,
        max_length=255,
        description="Optional custom project name (defaults to repository name)",
    )
    default_branch: str = Field(
        default="main",
        max_length=100,
        description="Default git branch to inspect",
    )

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        cleaned = v.strip()
        match = GITHUB_URL_REGEX.match(cleaned)
        if not match:
            raise ValueError(
                "Invalid GitHub repository URL. Must be in format https://github.com/owner/repo"
            )
        owner, repo = match.groups()
        if repo.endswith(".git"):
            repo = repo[:-4]
        return f"https://github.com/{owner}/{repo}"

    def get_normalized_name(self) -> str:
        """Derives a normalized project name from user input or the repository URL slug."""
        if self.name and self.name.strip():
            return self.name.strip()
        match = GITHUB_URL_REGEX.match(self.github_url)
        if match:
            _, repo = match.groups()
            if repo.endswith(".git"):
                repo = repo[:-4]
            return repo
        return "unnamed-project"


class ProjectResponse(BaseModel):
    """Schema for project identity and state representation."""

    id: uuid.UUID = Field(description="Unique project identifier")
    user_id: uuid.UUID = Field(description="Owner user identifier")
    name: str = Field(description="Project / repository display name")
    github_url: str = Field(description="Normalized GitHub repository URL")
    default_branch: str = Field(description="Default branch name")
    status: str = Field(description="Ingestion and analysis status")
    created_at: datetime = Field(description="Project creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)
