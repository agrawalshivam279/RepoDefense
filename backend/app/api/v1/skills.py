"""FastAPI REST router for candidate skills, weaknesses, and portfolio overviews."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.skill import (
    CandidateWeaknessResponse,
    RecordEvaluationRequest,
    RecordEvaluationResponse,
    ResolveWeaknessRequest,
    UserSkillResponse,
    UserSkillsOverviewResponse,
)
from app.services.weakness_tracker import (
    get_candidate_weaknesses,
    get_user_skills_overview,
    record_evaluation_turn,
    resolve_weakness,
)

router = APIRouter(tags=["Skills & Weaknesses"])


@router.get(
    "/overview",
    response_model=UserSkillsOverviewResponse,
    summary="Get candidate portfolio overview across skills and weaknesses",
)
async def get_skills_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSkillsOverviewResponse:
    """Returns aggregated skill proficiencies, weak/strong metrics, and top unresolved gaps."""
    return await get_user_skills_overview(session=db, user_id=current_user.id)


@router.get(
    "/weaknesses",
    response_model=List[CandidateWeaknessResponse],
    summary="List candidate weaknesses with optional filters",
)
async def list_weaknesses(
    project_id: Optional[uuid.UUID] = Query(default=None, description="Filter by project"),
    resolved: Optional[bool] = Query(default=None, description="Filter by resolution status"),
    category: Optional[str] = Query(default=None, description="Filter by skill category"),
    limit: int = Query(default=50, ge=1, le=100, description="Max records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CandidateWeaknessResponse]:
    """Returns candidate weakness records filtered by repository, category, or resolution state."""
    if project_id is not None:
        proj_stmt = select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        if (await db.execute(proj_stmt)).scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied",
            )

    weaknesses = await get_candidate_weaknesses(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        resolved=resolved,
        category=category,
        limit=limit,
    )
    return [CandidateWeaknessResponse.model_validate(w) for w in weaknesses]


@router.patch(
    "/weaknesses/{weakness_id}/resolve",
    response_model=CandidateWeaknessResponse,
    summary="Mark an identified weakness as resolved",
)
async def mark_weakness_resolved(
    weakness_id: uuid.UUID,
    payload: Optional[ResolveWeaknessRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateWeaknessResponse:
    """Marks a weakness resolved, records optional mentor feedback, and reinforces skill score."""
    feedback_note = payload.feedback if payload else None
    weakness = await resolve_weakness(
        session=db,
        weakness_id=weakness_id,
        user_id=current_user.id,
        feedback=feedback_note,
    )
    if weakness is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weakness record not found or access denied",
        )
    return CandidateWeaknessResponse.model_validate(weakness)


@router.post(
    "/evaluations",
    response_model=RecordEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record simulation evaluation turn and update candidate skills",
)
async def record_evaluation(
    payload: RecordEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordEvaluationResponse:
    """Processes an evaluation turn, updating UserSkill proficiency and extracting weaknesses."""
    proj_stmt = select(Project).where(
        Project.id == payload.project_id,
        Project.user_id == current_user.id,
    )
    if (await db.execute(proj_stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )

    skill, weakness = await record_evaluation_turn(
        session=db,
        user_id=current_user.id,
        project_id=payload.project_id,
        simulation_mode=payload.simulation_mode,
        category=payload.category,
        topic=payload.topic,
        question_prompt=payload.question_prompt,
        feedback=payload.feedback,
        passed=payload.passed,
        score=payload.score,
        session_id=payload.session_id,
        candidate_response=payload.candidate_response,
        severity=payload.severity,
    )

    skill_resp = UserSkillResponse.model_validate(skill)
    weakness_resp = (
        CandidateWeaknessResponse.model_validate(weakness) if weakness is not None else None
    )
    return RecordEvaluationResponse(skill=skill_resp, weakness=weakness_resp)
