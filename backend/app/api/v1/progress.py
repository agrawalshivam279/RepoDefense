"""FastAPI REST router for candidate skill progress, learning telemetry, and dashboard metrics."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.schemas.progress import (
    CategoryProgressDelta,
    ProficiencyTrendPoint,
    UserProgressOverviewResponse,
)
from app.services.skill_progress import (
    get_user_progress_overview,
    get_user_progress_timeline,
)

router = APIRouter(tags=["Skill Progress & Learning Telemetry"])


@router.get(
    "/overview",
    response_model=UserProgressOverviewResponse,
    summary="Get comprehensive candidate progress overview and telemetry",
)
async def get_progress_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProgressOverviewResponse:
    """Returns aggregated skill proficiency, velocity, streak, and focus areas for current user."""
    return await get_user_progress_overview(session=db, user_id=current_user.id)


@router.get(
    "/timeline",
    response_model=List[ProficiencyTrendPoint],
    summary="Get candidate skill proficiency progression timeline",
)
async def get_progress_timeline(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of trailing days for chronological timeline points",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProficiencyTrendPoint]:
    """Returns daily chronological proficiency and evaluation trajectory points."""
    return await get_user_progress_timeline(
        session=db,
        user_id=current_user.id,
        days=days,
    )


@router.get(
    "/categories",
    response_model=List[CategoryProgressDelta],
    summary="Get category-level progress deltas and resolution metrics",
)
async def get_category_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CategoryProgressDelta]:
    """Returns per-category proficiency levels, pass rates, and weakness resolution metrics."""
    overview = await get_user_progress_overview(session=db, user_id=current_user.id)
    return overview.category_deltas
