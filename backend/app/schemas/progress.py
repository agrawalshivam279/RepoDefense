"""Pydantic v2 data models for candidate skill progress, velocity, and telemetry."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProficiencyTrendPoint(BaseModel):
    """Historical proficiency progression bucket over time."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(
        ...,
        description="Date string formatted as YYYY-MM-DD",
    )
    average_proficiency: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Average skill proficiency on this date",
    )
    evaluations_count: int = Field(
        ...,
        ge=0,
        description="Cumulative or daily evaluations count",
    )
    passed_count: int = Field(
        ...,
        ge=0,
        description="Evaluations passed successfully",
    )


class WeaknessVelocityMetric(BaseModel):
    """Weakness remediation velocity and resolution metrics."""

    model_config = ConfigDict(from_attributes=True)

    total_identified: int = Field(..., ge=0, description="Total weaknesses identified")
    total_resolved: int = Field(..., ge=0, description="Total weaknesses remediated/resolved")
    resolution_rate_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of weaknesses resolved (0-100)",
    )
    critical_resolved: int = Field(0, ge=0)
    critical_total: int = Field(0, ge=0)
    major_resolved: int = Field(0, ge=0)
    major_total: int = Field(0, ge=0)
    minor_resolved: int = Field(0, ge=0)
    minor_total: int = Field(0, ge=0)
    average_resolution_hours: Optional[float] = Field(
        None,
        ge=0.0,
        description="Mean turnaround time in hours to remediate a weakness",
    )


class CategoryProgressDelta(BaseModel):
    """Category-level proficiency, pass rate, and weakness backlog metrics."""

    model_config = ConfigDict(from_attributes=True)

    category: str = Field(..., min_length=1, max_length=64)
    current_proficiency: float = Field(..., ge=0.0, le=100.0)
    total_evaluations: int = Field(..., ge=0)
    passed_evaluations: int = Field(..., ge=0)
    pass_rate_pct: float = Field(..., ge=0.0, le=100.0)
    total_weaknesses: int = Field(..., ge=0)
    resolved_weaknesses: int = Field(..., ge=0)
    status: str = Field(
        ...,
        description=(
            "Mastery status: mastered (>=80), proficient (>=65), "
            "improving (>=50), needs_focus (<50)"
        ),
    )


class TopicMasteryItem(BaseModel):
    """Individual topic mastery breakdown with evaluation tracking."""

    model_config = ConfigDict(from_attributes=True)

    topic: str = Field(..., min_length=1, max_length=128)
    category: str = Field(..., min_length=1, max_length=64)
    proficiency_score: float = Field(..., ge=0.0, le=100.0)
    evaluations: int = Field(..., ge=0)
    pass_rate_pct: float = Field(..., ge=0.0, le=100.0)
    last_evaluated_at: Optional[datetime] = Field(None)


class UserProgressOverviewResponse(BaseModel):
    """Unified telemetry overview aggregating candidate trajectory, velocity, and focus areas."""

    model_config = ConfigDict(from_attributes=True)

    overall_proficiency: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Mean proficiency across all tracked technical skills",
    )
    total_evaluations: int = Field(..., ge=0)
    total_passed: int = Field(..., ge=0)
    overall_pass_rate_pct: float = Field(..., ge=0.0, le=100.0)
    active_skills_count: int = Field(..., ge=0)
    mastered_skills_count: int = Field(
        ...,
        ge=0,
        description="Skills with proficiency >= 80.0",
    )
    learning_streak_days: int = Field(
        ...,
        ge=0,
        description="Consecutive active days with recorded evaluations or remediations",
    )
    weakness_velocity: WeaknessVelocityMetric
    category_deltas: List[CategoryProgressDelta] = Field(default_factory=list)
    recent_timeline: List[ProficiencyTrendPoint] = Field(default_factory=list)
    top_improved_topics: List[TopicMasteryItem] = Field(default_factory=list)
    needs_focus_topics: List[TopicMasteryItem] = Field(default_factory=list)
