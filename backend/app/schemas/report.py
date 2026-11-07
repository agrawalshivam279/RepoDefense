"""Pydantic schemas and data contracts for defense interview evaluation reports."""

import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionCategory


class CategoryScore(BaseModel):
    """Aggregate score and qualitative evaluation for a specific architectural category."""

    category: QuestionCategory = Field(
        ..., description="Architectural domain (architecture, scalability, etc.)"
    )
    score: float = Field(
        ..., ge=0.0, le=10.0, description="Aggregated score on a 1.0 - 10.0 scale"
    )
    questions_count: int = Field(
        ..., ge=1, description="Number of questions evaluated in this category"
    )
    status: str = Field(
        ..., description="Evaluation classification: passed, needs_work, or remediated"
    )
    summary: str = Field(
        ..., description="Qualitative evaluation summary for this category"
    )

    model_config = ConfigDict(extra="ignore")


class ReportSynthesisOutput(BaseModel):
    """Structured output expected from the Principal Engineer LLM report generator."""

    verdict: str = Field(
        ..., description="Overall architectural verdict (e.g. Certified Principal Defense)"
    )
    summary: str = Field(
        ..., description="Executive summary of the candidate's codebase understanding"
    )
    key_strengths: List[str] = Field(
        default_factory=list,
        description="Key architectural strengths demonstrated during defense",
    )
    critical_blind_spots: List[str] = Field(
        default_factory=list,
        description="Architectural blind spots or gaps identified under stress testing",
    )
    actionable_recommendations: List[str] = Field(
        default_factory=list,
        description="Targeted technical recommendations to remediate blind spots",
    )

    model_config = ConfigDict(extra="ignore")


class DefenseReportResponse(BaseModel):
    """API response model for a completed defense session report."""

    session_id: uuid.UUID = Field(..., description="Unique defense session UUID")
    project_id: uuid.UUID = Field(..., description="Target project UUID")
    overall_score: float = Field(
        ..., ge=0.0, le=10.0, description="Final overall score on a 1.0 - 10.0 scale"
    )
    verdict: str = Field(..., description="Overall defensibility verdict")
    summary: str = Field(..., description="Executive assessment summary")
    category_scores: List[CategoryScore] = Field(
        default_factory=list, description="Score breakdown by architectural category"
    )
    key_strengths: List[str] = Field(
        default_factory=list, description="Top architectural strengths"
    )
    critical_blind_spots: List[str] = Field(
        default_factory=list, description="Key architectural blind spots"
    )
    actionable_recommendations: List[str] = Field(
        default_factory=list, description="Actionable architectural mitigations"
    )
    total_questions: int = Field(
        ..., ge=1, description="Total number of technical questions defended"
    )
    completed_at: str = Field(..., description="ISO 8601 completion timestamp")

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class EnhancedDefenseReportResponse(DefenseReportResponse):
    """Extended defense evaluation report enriched with architectural context and tech audit."""

    architecture_primary_pattern: str | None = Field(
        None, description="Primary detected architecture pattern name"
    )
    architecture_confidence_tier: str | None = Field(
        None, description="Pattern detection confidence tier (high, moderate, low)"
    )
    diagram_mermaid_code: str | None = Field(
        None, description="Synthesized Mermaid flowchart syntax for system topology"
    )
    tech_health_score: int | None = Field(
        None, ge=0, le=100, description="Technology stack health score (0-100%)"
    )
    tech_flagged_count: int | None = Field(
        None, ge=0, description="Count of flagged obsolete or vulnerable dependencies"
    )
    tech_total_dependencies: int | None = Field(
        None, ge=0, description="Total count of inspected dependencies"
    )
    claims_verified_count: int | None = Field(
        None, ge=0, description="Count of verified resume technical claims"
    )
    claims_total_count: int | None = Field(
        None, ge=0, description="Total count of extracted resume claims"
    )

    model_config = ConfigDict(from_attributes=True, extra="ignore")
