import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.tech_audit import TechAuditReportResponse
from app.services.tech_audit import audit_project_technology

router = APIRouter(tags=["Technology Audit"])


@router.get(
    "/projects/{project_id}/tech-audit",
    response_model=TechAuditReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Conduct dependency and technology health audit",
    description=(
        "Analyzes repository dependencies against curated obsolescence rules, "
        "known CVE security thresholds, and deprecated packages to produce a "
        "technology health score (0-100%) and remediation guidance."
    ),
)
async def get_project_tech_audit(
    project_id: Annotated[
        uuid.UUID,
        Path(description="Unique UUID of the project"),
    ],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechAuditReportResponse:
    """Retrieve technology obsolescence and health audit for a project."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project's technology audit",
        )

    return await audit_project_technology(project, db)
