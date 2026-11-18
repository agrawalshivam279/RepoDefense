"""
Pydantic v2 schemas for the Phase 4 Learning Loop health & diagnostic probe.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComponentHealthStatus(str, Enum):
    """Operational health status for a subsystem component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseModelsHealth(BaseModel):
    """Database model connectivity and row count diagnostics."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentHealthStatus = Field(..., description="Component status")
    user_skills_accessible: bool = Field(
        ..., description="Whether user_skills table is queried"
    )
    candidate_weaknesses_accessible: bool = Field(
        ..., description="Whether candidate_weaknesses table is queried"
    )
    total_user_skills: int = Field(
        default=0, ge=0, description="Total user_skill records"
    )
    total_candidate_weaknesses: int = Field(
        default=0, ge=0, description="Total candidate_weakness records"
    )
    detail: Optional[str] = Field(
        default=None, description="Diagnostic details or error message"
    )


class BenchmarkProfilesHealth(BaseModel):
    """Integrity status of the senior engineering benchmark profile catalog."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentHealthStatus = Field(..., description="Component status")
    configured_tiers: list[str] = Field(
        ..., description="List of configured benchmark tiers"
    )
    total_categories: int = Field(
        ..., ge=0, description="Number of domains per profile tier"
    )
    tier_integrity_verified: bool = Field(
        ..., description="True if all weights and targets pass validation"
    )
    detail: Optional[str] = Field(
        default=None, description="Diagnostic details or error message"
    )


class MentorServiceHealth(BaseModel):
    """Readiness status of Mentor Mode teaching synthesizers and offline fallbacks."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentHealthStatus = Field(..., description="Component status")
    fallbacks_ready: bool = Field(
        ..., description="Whether deterministic fallbacks are loaded"
    )
    supported_fallback_topics: list[str] = Field(
        ..., description="List of pre-compiled offline topics"
    )
    detail: Optional[str] = Field(
        default=None, description="Diagnostic details or error message"
    )


class RetestServiceHealth(BaseModel):
    """Operational telemetry for Targeted Re-Testing session generation and cache."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentHealthStatus = Field(..., description="Component status")
    cache_active: bool = Field(
        ..., description="Whether bounded question cache is initialized"
    )
    cached_question_count: int = Field(
        default=0, ge=0, description="Questions currently in FIFO cache"
    )
    max_cache_capacity: int = Field(
        ..., ge=1, description="Maximum cache capacity before LRU/FIFO pruning"
    )
    detail: Optional[str] = Field(
        default=None, description="Diagnostic details or error message"
    )


class LearningLoopHealthResponse(BaseModel):
    """Aggregated health and diagnostic readiness report for Phase 4 Learning Loop."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentHealthStatus = Field(
        ..., description="Overall aggregated learning loop health"
    )
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version string")
    database_models: DatabaseModelsHealth = Field(
        ..., description="Database model table diagnostics"
    )
    benchmark_profiles: BenchmarkProfilesHealth = Field(
        ..., description="Senior benchmark catalog health"
    )
    mentor_service: MentorServiceHealth = Field(
        ..., description="Mentor service and fallback readiness"
    )
    retest_service: RetestServiceHealth = Field(
        ..., description="Targeted retest session cache health"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC inspection timestamp",
    )
