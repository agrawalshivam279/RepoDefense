"""Pydantic v2 schemas for Public Shareable Defense Reports and Verification Badges."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionCategory


class CreateShareTokenRequest(BaseModel):
    """Payload to configure or toggle public report sharing."""

    is_active: bool = Field(
        default=True,
        description="Whether this defense report is publicly accessible",
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Optional duration in days before public link expires",
    )

    model_config = ConfigDict(extra="forbid")


class PublicShareTokenResponse(BaseModel):
    """Response containing public share credentials and embed snippets."""

    session_id: str = Field(..., description="Unique defense session identifier")
    project_id: str = Field(..., description="Target project UUID string")
    share_token: str = Field(..., description="Cryptographic unguessable share token")
    share_url: str = Field(..., description="Canonical public verification web URL")
    badge_url: str = Field(..., description="Direct SVG badge image URL")
    markdown_badge: str = Field(..., description="Ready-to-paste Markdown badge syntax")
    html_badge: str = Field(..., description="Ready-to-paste HTML badge snippet")
    is_active: bool = Field(..., description="Whether the share link is currently active")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    expires_at: Optional[str] = Field(None, description="Optional ISO 8601 expiration timestamp")

    model_config = ConfigDict(extra="forbid")


class PublicCategoryScore(BaseModel):
    """Public-safe architectural domain evaluation summary."""

    category: QuestionCategory = Field(..., description="Architectural domain")
    score: float = Field(..., ge=0.0, le=10.0, description="Category score on a 1.0 - 10.0 scale")
    questions_count: int = Field(..., ge=1, description="Questions evaluated in this domain")
    status: str = Field(..., description="Domain classification (passed, needs_work, remediated)")
    summary: str = Field(..., description="Executive qualitative domain summary")

    model_config = ConfigDict(extra="forbid")


class PublicDefenseReportResponse(BaseModel):
    """Public read-only verified architectural defense report."""

    verification_id: str = Field(..., description="Cryptographic verification token")
    project_name: str = Field(..., description="Target repository name")
    github_url: str = Field(..., description="Public GitHub repository URL")
    commit_hash: str = Field(
        ..., description="Verified snapshot commit hash (abbreviated or full)"
    )
    overall_score: float = Field(
        ..., ge=0.0, le=10.0, description="Overall defense score (1.0 - 10.0)"
    )
    verdict: str = Field(..., description="Formal architectural defensibility verdict")
    certification_tier: str = Field(
        ...,
        description=(
            "Standardized certification tier (Certified Principal, "
            "Solid Architect, Remediation Required)"
        ),
    )
    summary: str = Field(..., description="Executive assessment summary")
    category_scores: List[PublicCategoryScore] = Field(
        default_factory=list,
        description="Public-safe category breakdowns",
    )
    key_strengths: List[str] = Field(
        default_factory=list,
        description="Verified architectural strengths",
    )
    critical_blind_spots: List[str] = Field(
        default_factory=list,
        description="Architectural blind spots or growth opportunities",
    )
    architecture_primary_pattern: Optional[str] = Field(
        None,
        description="Primary detected architectural pattern",
    )
    tech_health_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Overall technology and dependency health score",
    )
    total_questions: int = Field(..., ge=1, description="Total technical questions defended")
    completed_at: str = Field(..., description="ISO 8601 defense completion timestamp")
    verified_at: str = Field(..., description="ISO 8601 public verification timestamp")
    issuer: str = Field(default="RepoDefense Verifier", description="Verification authority")

    model_config = ConfigDict(extra="forbid")
