"""Service for conducting dependency technology health audits on repositories."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.tech_audit import audit_dependencies_list
from app.models.analysis import Dependency
from app.models.project import Project
from app.schemas.tech_audit import TechAuditReportResponse

logger = structlog.get_logger(__name__)


async def audit_project_technology(
    project: Project,
    db: AsyncSession,
) -> TechAuditReportResponse:
    """Performs a technology stack and dependency obsolescence audit for a project."""
    stmt = (
        select(Dependency.name, Dependency.version, Dependency.is_dev)
        .where(Dependency.project_id == project.id)
        .order_by(Dependency.name.asc())
    )
    result = await db.execute(stmt)
    records = result.all()

    dependencies = [(row[0], row[1], bool(row[2])) for row in records]
    total_count = len(dependencies)

    flagged_items, health_score, counts = audit_dependencies_list(dependencies)

    logger.info(
        "tech_audit_completed",
        project_id=str(project.id),
        total_dependencies=total_count,
        flagged_count=len(flagged_items),
        health_score=health_score,
    )

    return TechAuditReportResponse(
        project_id=str(project.id),
        project_name=project.name,
        total_dependencies_audited=total_count,
        flagged_dependencies_count=len(flagged_items),
        critical_count=counts["critical"],
        high_count=counts["high"],
        medium_count=counts["medium"],
        low_count=counts["low"],
        tech_health_score=health_score,
        audited_items=flagged_items,
    )
