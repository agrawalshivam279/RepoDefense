"""Pydantic v2 data models for dependency technology audits and obsolescence inspection."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AuditSeverity(str, Enum):
    """Severity tier for flagged dependency obsolescence or vulnerabilities."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuditCategory(str, Enum):
    """Categorization of dependency issue."""

    DEPRECATED = "deprecated"
    SECURITY_RISK = "security_risk"
    OUTDATED = "outdated"
    UNMAINTAINED = "unmaintained"


class AuditedDependencyItem(BaseModel):
    """Single dependency evaluated with flagged issue, severity, and remediation."""

    name: str
    version: str | None = None
    is_dev: bool = False
    severity: AuditSeverity
    category: AuditCategory
    issue_description: str
    suggested_alternative: str
    reference_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TechAuditReportResponse(BaseModel):
    """Aggregated technology health audit response for a repository."""

    project_id: str
    project_name: str
    total_dependencies_audited: int
    flagged_dependencies_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    tech_health_score: int = Field(..., ge=0, le=100)
    audited_items: list[AuditedDependencyItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
