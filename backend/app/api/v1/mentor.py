"""FastAPI REST router for Mentor Mode teaching content, code remediation & mini challenges."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.challenge_generator import evaluate_mini_challenge, generate_mini_challenge
from app.ai.mentor_generator import generate_mentor_explanation
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import User
from app.models.skill import CandidateWeakness
from app.schemas.challenge import (
    ChallengeEvaluationResponse,
    GenerateChallengeRequest,
    MiniChallengeDifficulty,
    MiniChallengeResponse,
    SubmitChallengeSolutionRequest,
)
from app.schemas.mentor import (
    MentorExplanationRequest,
    MentorExplanationResponse,
)
from app.services.weakness_tracker import resolve_weakness

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
    """Generate architectural explanation, before/after code examples, and Socratic challenge."""
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
    """Load an existing weakness and synthesize pedagogical mentor guidance and remediation."""
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


@router.post(
    "/challenges/generate",
    response_model=MiniChallengeResponse,
    summary="Generate an architectural mini-challenge for a topic or recorded weakness",
)
async def generate_challenge(
    request: GenerateChallengeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MiniChallengeResponse:
    """Generate a targeted architectural coding challenge with starter code and criteria."""
    category = request.category or "architecture"
    topic = request.topic or ""
    question_prompt: Optional[str] = None
    candidate_response: Optional[str] = None
    feedback: Optional[str] = None

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
        question_prompt = weakness.question_prompt
        candidate_response = weakness.candidate_response
        feedback = weakness.feedback

    if not topic.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty 'topic' is required to generate a mini-challenge.",
        )

    return await generate_mini_challenge(
        category=category,
        topic=topic,
        difficulty=request.difficulty,
        language=request.language,
        question_prompt=question_prompt,
        candidate_response=candidate_response,
        feedback=feedback,
        code_context=request.code_context,
        model=request.model,
        llm_base_url=request.llm_base_url,
        llm_api_key=request.llm_api_key,
    )


@router.get(
    "/challenges/weakness/{weakness_id}",
    response_model=MiniChallengeResponse,
    summary="Generate a mini-challenge directly anchored in a candidate weakness",
)
async def get_challenge_for_weakness(
    weakness_id: uuid.UUID,
    difficulty: MiniChallengeDifficulty = Query(default=MiniChallengeDifficulty.INTERMEDIATE),
    language: str = Query(default="python", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MiniChallengeResponse:
    """Load a candidate weakness and generate a targeted architectural challenge."""
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

    return await generate_mini_challenge(
        category=weakness.category,
        topic=weakness.topic,
        difficulty=difficulty,
        language=language,
        question_prompt=weakness.question_prompt,
        candidate_response=weakness.candidate_response,
        feedback=weakness.feedback,
    )


@router.post(
    "/challenges/evaluate",
    response_model=ChallengeEvaluationResponse,
    summary="Evaluate candidate's solution for an architectural mini-challenge",
)
async def evaluate_challenge(
    request: SubmitChallengeSolutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeEvaluationResponse:
    """Evaluate candidate solution and update linked weakness/skill when passing."""
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
        if weakness.topic.lower() != request.topic.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Challenge topic '{request.topic}' does not match "
                    f"linked weakness topic '{weakness.topic}'."
                ),
            )

    eval_result = await evaluate_mini_challenge(
        challenge_id=request.challenge_id,
        category=request.category,
        topic=request.topic,
        scenario=request.scenario,
        requirements=request.requirements,
        candidate_solution=request.candidate_solution,
        language=request.language,
        model=request.model,
        llm_base_url=request.llm_base_url,
        llm_api_key=request.llm_api_key,
    )

    if eval_result.passed and request.weakness_id:
        await resolve_weakness(
            session=db,
            weakness_id=request.weakness_id,
            user_id=current_user.id,
            feedback=f"Resolved via Mini Challenge: {eval_result.critique[:128]}",
        )
        await db.commit()
        eval_result.weakness_updated = True

    return eval_result
