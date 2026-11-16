"""FastAPI REST router for Mentor Mode teaching content and code remediation."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mentor_generator import generate_mentor_explanation
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.models.skill import CandidateWeakness
from app.schemas.mentor import (
    MentorExplanationRequest,
    MentorExplanationResponse,
)

router = APIRouter(tags=["Mentor Mode"])


@router.post(
    "/explain",
    response_model=MentorExplanationResponse,
    summary="Synthesize architectural mentor teaching content and drop-in code remediation",
)
async def explain_weakness_or_topic(
    request: MentorExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MentorExplanationResponse:
    """Generate architectural explanation, before/after code examples, and Socratic challenge.

    If weakness_id is provided, loads context from candidate_weaknesses under strict multi-tenant
    ownership checks. Otherwise, uses the inline request parameters.
    """
    category = request.category or "architecture"
    topic = request.topic or ""
    question_prompt = request.question_prompt
    candidate_response = request.candidate_response
    feedback = request.feedback

    if request.weakness_id:
        stmt = select(CandidateWeakness).where(
            CandidateWeakness.id == request.weakness_id,
            CandidateWeakness.user_id == current_user.id,
        )
        weakness: Optional[CandidateWeakness] = (await db.execute(stmt)).scalar_one_or_none()
        if not weakness:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Weakness record not found or access denied.",
            )
        category = request.category or weakness.category
        topic = request.topic or weakness.topic
        question_prompt = request.question_prompt or weakness.question_prompt
        candidate_response = request.candidate_response or weakness.candidate_response
        feedback = request.feedback or weakness.feedback

    if not topic.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty 'topic' is required to generate mentor teaching content.",
        )

    return await generate_mentor_explanation(
        category=category,
        topic=topic,
        question_prompt=question_prompt,
        candidate_response=candidate_response,
        feedback=feedback,
        code_context=request.code_context,
        language=request.language,
        model=request.model,
        llm_base_url=request.llm_base_url,
        llm_api_key=request.llm_api_key,
    )


@router.get(
    "/explanations/{weakness_id}",
    response_model=MentorExplanationResponse,
    summary="Generate mentor teaching content directly for a recorded candidate weakness",
)
async def get_explanation_for_weakness(
    weakness_id: uuid.UUID,
    language: str = Query(default="python", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MentorExplanationResponse:
    """Load an existing weakness and synthesize pedagogical mentor guidance and remediation.

    Guarantees multi-tenant isolation by returning 404 if the record belongs to another user.
    """
    stmt = select(CandidateWeakness).where(
        CandidateWeakness.id == weakness_id,
        CandidateWeakness.user_id == current_user.id,
    )
    weakness: Optional[CandidateWeakness] = (await db.execute(stmt)).scalar_one_or_none()
    if not weakness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weakness record not found or access denied.",
        )

    return await generate_mentor_explanation(
        category=weakness.category,
        topic=weakness.topic,
        question_prompt=weakness.question_prompt,
        candidate_response=weakness.candidate_response,
        feedback=weakness.feedback,
        language=language,
    )
