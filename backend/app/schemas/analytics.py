"""Pydantic v2 contracts for cross-mode performance analytics and visualizations."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DefenseModeKey(str, Enum):
    """Canonical defense simulation modes tracked in analytics."""

    CORE_DEFENSE = "core_defense"
    PR_DEFENSE = "pr_defense"
    COMMIT_DEFENSE = "commit_defense"
    STRESS_TEST = "stress_test"
    INCIDENT_SIMULATION = "incident_simulation"
    ARCH_DEFENSE = "arch_defense"


class ModePerformanceMetric(BaseModel):
    """Aggregated performance summary for a single defense mode."""

    mode: DefenseModeKey = Field(..., description="Canonical defense mode identifier")
    label: str = Field(..., description="Human-readable defense mode label")
    sessions_total: int = Field(default=0, ge=0, description="Total sessions started")
    sessions_completed: int = Field(default=0, ge=0, description="Completed sessions")
    avg_score_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Mean normalized score (0-100)"
    )
    best_score_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Highest normalized score (0-100)"
    )
    pass_rate_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Percentage scoring >= 70.0"
    )

    model_config = ConfigDict(extra="ignore")


class ScoreTrendPoint(BaseModel):
    """Single chronological data point for performance trend charts."""

    session_id: str = Field(..., description="Session identifier")
    mode: DefenseModeKey = Field(..., description="Defense mode for the session")
    label: str = Field(..., description="Display label for the mode")
    score_pct: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 score")
    timestamp: str = Field(..., description="ISO 8601 completion or update timestamp")
    topic_or_title: str = Field(..., description="Scenario, PR, commit, or topic title")

    model_config = ConfigDict(extra="ignore")


class CategorySkillMetric(BaseModel):
    """Aggregated confidence metric for an architectural topic or component skill."""

    category: str = Field(..., description="Technical category (e.g. database, auth)")
    confidence_pct: float = Field(..., ge=0.0, le=100.0, description="Confidence 0-100%")
    evaluations_count: int = Field(default=1, ge=1, description="Number of skill readings")

    model_config = ConfigDict(extra="ignore")


class LanguageDistributionItem(BaseModel):
    """Language composition breakdown for an analyzed codebase snapshot."""

    language: str = Field(..., description="Programming or config language name")
    file_count: int = Field(default=0, ge=0, description="Files counted")
    total_lines: int = Field(default=0, ge=0, description="Physical lines of code")
    line_share_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Share of lines")

    model_config = ConfigDict(extra="ignore")


class ModuleCoveragePoint(BaseModel):
    """Directory module coverage datapoint for analytics heatmaps and bar charts."""

    module_path: str = Field(..., description="Directory module prefix")
    coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Module coverage %")
    tested_files: int = Field(default=0, ge=0, description="Defended files count")
    total_files: int = Field(default=0, ge=0, description="Total cataloged files")

    model_config = ConfigDict(extra="ignore")


class ProjectAnalyticsResponse(BaseModel):
    """Comprehensive cross-mode performance & repository ground-truth analytics."""

    project_id: str = Field(..., description="Target repository UUID")
    project_name: str = Field(..., description="Repository display name")
    overall_readiness_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Aggregate normalized score across modes"
    )
    total_sessions: int = Field(default=0, ge=0, description="All sessions across modes")
    completed_sessions: int = Field(default=0, ge=0, description="Completed sessions across modes")
    file_coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="File coverage %")
    evidence_coverage_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Evidence coverage %"
    )
    tech_health_score: Optional[int] = Field(
        default=None, ge=0, le=100, description="Static dependency health score (0-100)"
    )
    mode_breakdown: List[ModePerformanceMetric] = Field(default_factory=list)
    category_skills: List[CategorySkillMetric] = Field(default_factory=list)
    score_trend: List[ScoreTrendPoint] = Field(default_factory=list)
    language_distribution: List[LanguageDistributionItem] = Field(default_factory=list)
    module_coverage: List[ModuleCoveragePoint] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class WorkspaceAnalyticsSummary(BaseModel):
    """Cross-project analytics overview scoped strictly to the authenticated user."""

    total_projects: int = Field(default=0, ge=0, description="Registered repositories")
    analyzed_projects: int = Field(default=0, ge=0, description="Analyzed repositories")
    total_sessions: int = Field(default=0, ge=0, description="All user sessions across modes")
    completed_sessions: int = Field(default=0, ge=0, description="Completed user sessions")
    avg_readiness_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Average score across completed sessions"
    )
    mode_breakdown: List[ModePerformanceMetric] = Field(default_factory=list)
    recent_trend: List[ScoreTrendPoint] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
