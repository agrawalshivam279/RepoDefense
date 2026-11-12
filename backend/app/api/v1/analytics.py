"""FastAPI REST router for cross-mode performance analytics and visualizations."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.schemas.analytics import ProjectAnalyticsResponse, WorkspaceAnalyticsSummary
from app.services.analytics import build_project_analytics, build_workspace_analytics

router = APIRouter(tags=["Analytics"])


@router.get(
    "/workspace",
    response_model=WorkspaceAnalyticsSummary,
    summary="Get aggregated cross-project performance analytics for the current user",
)
async def get_workspace_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceAnalyticsSummary:
    """Returns cross-mode defense statistics aggregated across all user-owned repositories."""
    return await build_workspace_analytics(current_user.id, db)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectAnalyticsResponse,
    summary="Get project performance analytics, coverage, skills, and score trend",
)
async def get_project_analytics(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectAnalyticsResponse:
    """Returns comprehensive analytics for a single user-owned project."""
    return await build_project_analytics(project_id, current_user.id, db)
