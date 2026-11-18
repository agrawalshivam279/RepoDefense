"""
FastAPI router for Senior & Principal Engineer Skill Gap Analysis.
Provides comparative gap metrics and remediation suggestions against industry benchmarks.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.schemas.skill_gap import (
    SkillGapAnalysisResponse,
    TargetRoleBenchmark,
)
from app.services.skill_gap import skill_gap_service

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Skill Gap Analysis"])


@router.get(
    "/gap-analysis",
    response_model=SkillGapAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate comparative skill gap analysis against target engineering seniority",
)
async def get_skill_gap_analysis(
    target_role: TargetRoleBenchmark = Query(
        default=TargetRoleBenchmark.SENIOR_ENGINEER,
        description="Target engineering seniority benchmark to compare skills against",
    ),
    project_id: UUID | None = Query(
        default=None,
        description="Optional project ID to filter project-specific active weaknesses",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillGapAnalysisResponse:
    """
    Evaluates candidate's skill matrix against standardized industry benchmarks.
    Calculates category-level deficits, overall role readiness %, and returns
    prioritized remediation recommendations.
    """
    logger.info(
        "fetching_skill_gap_analysis",
        user_id=str(current_user.id),
        target_role=target_role.value,
        project_id=str(project_id) if project_id else None,
    )
    return await skill_gap_service.analyze_skill_gaps(
        db=db,
        user_id=current_user.id,
        target_role=target_role,
        project_id=project_id,
    )
