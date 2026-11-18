"""
Skill Gap Analysis Pydantic schemas and benchmark data models.
Provides structured contracts for comparing candidate skills against industry standards.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TargetRoleBenchmark(str, Enum):
    """Target engineering seniority benchmark tiers."""
    MID_LEVEL = "mid_level"
    SENIOR_ENGINEER = "senior_engineer"
    STAFF_PRINCIPAL = "staff_principal"


class GapStatus(str, Enum):
    """Categorical gap evaluation status."""
    SURPASSED = "surpassed"
    MET = "met"
    MODERATE_GAP = "moderate_gap"
    CRITICAL_GAP = "critical_gap"


class RemediationPriority(str, Enum):
    """Remediation urgency level."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CategoryGapMetric(BaseModel):
    """Deficit and benchmark comparison metric for a technical category."""
    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=1, max_length=100)
    current_score: float = Field(..., ge=0.0, le=100.0)
    benchmark_score: float = Field(..., ge=0.0, le=100.0)
    gap_deficit: float = Field(..., ge=0.0, le=100.0)
    status: GapStatus
    weight: float = Field(..., gt=0.0, le=5.0)
    percentile_estimate: float = Field(..., ge=0.0, le=100.0)


class RemediationRecommendation(BaseModel):
    """Actionable remediation recommendation targeting a specific gap."""
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=1, max_length=150)
    category: str = Field(..., min_length=1, max_length=100)
    priority: RemediationPriority
    rationale: str = Field(..., min_length=5, max_length=1000)
    unresolved_weakness_count: int = Field(default=0, ge=0)
    suggested_action: str = Field(..., min_length=5, max_length=500)


class SkillGapAnalysisResponse(BaseModel):
    """Full skill gap analysis payload comparing candidate to standard engineering bar."""
    model_config = ConfigDict(extra="forbid")

    target_role: TargetRoleBenchmark
    overall_candidate_score: float = Field(..., ge=0.0, le=100.0)
    overall_benchmark_score: float = Field(..., ge=0.0, le=100.0)
    overall_readiness_pct: float = Field(..., ge=0.0, le=100.0)
    categories: list[CategoryGapMetric]
    recommendations: list[RemediationRecommendation]
    strengths: list[str]
    critical_gaps: list[str]
    analyzed_at: datetime
