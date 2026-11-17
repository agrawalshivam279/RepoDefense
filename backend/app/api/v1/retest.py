"""FastAPI REST router for Targeted Re-Testing and Weakness Remediation."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.schemas.retest import (
    EligibleWeaknessesResponse,
    RetestEvaluationResponse,
    SubmitRetestAnswerRequest,
    TargetedRetestSessionCreate,
    TargetedRetestSessionResponse,
)
from app.services.retest_service import (
    RetestNotFoundError,
    create_targeted_retest_session,
    evaluate_retest_answer,
    get_eligible_retest_weaknesses,
)

router = APIRouter(tags=["Targeted Re-Testing"])


@router.get(
    "/weaknesses",
    response_model=EligibleWeaknessesResponse,
    summary="List candidate weaknesses eligible for targeted re-testing",
)
async def list_eligible_weaknesses(
    project_id: Optional[uuid.UUID] = Query(
        default=None, description="Optional project filter"
    ),
    category: Optional[str] = Query(
        default=None, max_length=64, description="Optional category filter"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EligibleWeaknessesResponse:
    """Returns active, unresolved weaknesses scoped to the authenticated candidate."""
    return await get_eligible_retest_weaknesses(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        category=category,
    )


@router.post(
    "/session",
    response_model=TargetedRetestSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a targeted re-test session focusing on active weaknesses",
)
async def create_retest_session(
    payload: TargetedRetestSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TargetedRetestSessionResponse:
    """Generates targeted re-test questions specifically grounded in candidate's past failures."""
    return await create_targeted_retest_session(
        session=db,
        user_id=current_user.id,
        project_id=payload.project_id,
        weakness_ids=payload.weakness_ids,
        category=payload.category,
        max_questions=payload.max_questions,
    )


@router.post(
    "/evaluate",
    response_model=RetestEvaluationResponse,
    summary="Evaluate candidate defense on a targeted re-test question",
)
async def evaluate_retest(
    payload: SubmitRetestAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetestEvaluationResponse:
    """Evaluates the candidate's re-test defense, resolves weakness if passed, and updates skill."""
    try:
        return await evaluate_retest_answer(
            session=db,
            user_id=current_user.id,
            session_id=payload.session_id,
            question_id=payload.question_id,
            weakness_id=payload.weakness_id,
            candidate_response=payload.candidate_response,
        )
    except RetestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
