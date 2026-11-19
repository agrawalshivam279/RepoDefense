from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class GitHubAppStatusResponse(BaseModel):
    """Status indicating whether GitHub App integration is configured and active."""

    configured: bool = Field(..., description="Whether GitHub App credentials are set")
    app_id: Optional[str] = Field(None, description="Configured GitHub App ID")
    app_slug: Optional[str] = Field(None, description="Configured GitHub App slug")
    install_url: Optional[str] = Field(None, description="Direct URL to install GitHub App")


class GitHubAppRepoItem(BaseModel):
    """Metadata for a repository accessible via a GitHub App installation."""

    id: int = Field(..., description="GitHub repository ID")
    name: str = Field(..., description="Repository short name")
    full_name: str = Field(..., description="Repository full owner/name")
    private: bool = Field(..., description="Whether repository is private")
    default_branch: str = Field("main", description="Default branch name")
    description: Optional[str] = Field(None, description="Repository description")
    clone_url: str = Field(..., description="HTTPS clone URL")
    html_url: str = Field(..., description="Repository web URL")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class GitHubAppRepoListResponse(BaseModel):
    """Paginated list of repositories accessible under an installation."""

    installation_id: int = Field(..., description="GitHub App installation ID")
    total_count: int = Field(..., description="Total accessible repositories count")
    repositories: List[GitHubAppRepoItem] = Field(
        default_factory=list, description="Accessible repository items"
    )


class PrivateRepoProjectCreate(BaseModel):
    """Payload to register a private repository for defense analysis."""

    full_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Repository full name in 'owner/repo' format",
    )
    installation_id: int = Field(
        ...,
        gt=0,
        description="GitHub App installation ID granting access",
    )
    default_branch: str = Field(
        "main",
        min_length=1,
        max_length=100,
        description="Target branch to clone and evaluate",
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name_format(cls, value: str) -> str:
        """Ensures repository name matches 'owner/repo' structure."""
        cleaned = value.strip()
        parts = cleaned.split("/")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ValueError("Repository full_name must be in 'owner/repo' format")
        return cleaned


class GitHubWebhookResponse(BaseModel):
    """Response returned upon processing a GitHub webhook event."""

    status: str = Field("ok", description="Processing status")
    event: str = Field(..., description="GitHub event type from X-GitHub-Event header")
    action: Optional[str] = Field(None, description="Action sub-type if present")
    message: Optional[str] = Field(None, description="Informational message")
