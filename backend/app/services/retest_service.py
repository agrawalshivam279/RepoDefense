"""Domain service for Targeted Re-Testing session orchestration and evaluation."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.retest_fallbacks import get_fallback_retest_question
from app.ai.retest_generator import (
    evaluate_targeted_retest_defense,
    generate_targeted_retest_question,
)
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.retest import (
    EligibleWeaknessesResponse,
    EligibleWeaknessItem,
    RetestEvaluationResponse,
    RetestQuestion,
    TargetedRetestSessionResponse,
)
from app.services.weakness_tracker import resolve_weakness

logger = structlog.get_logger(__name__)

# In-memory registry for active re-test questions with automatic DB fallback
_ACTIVE_RETEST_QUESTIONS: Dict[str, Dict[str, Any]] = {}


async def get_eligible_retest_weaknesses(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
) -> EligibleWeaknessesResponse:
    """Retrieve unresolved weaknesses eligible for targeted re-testing."""
    stmt = (
        select(CandidateWeakness)
        .where(
            CandidateWeakness.user_id == user_id,
            CandidateWeakness.resolved.is_(False),
        )
        .order_by(desc(CandidateWeakness.created_at))
    )
    if project_id is not None:
        stmt = stmt.where(CandidateWeakness.project_id == project_id)
    if category is not None:
        stmt = stmt.where(CandidateWeakness.category == category.strip().lower()[:64])

    res = await session.execute(stmt)
    weaknesses = list(res.scalars().all())

    items = [
        EligibleWeaknessItem(
            id=w.id,
            project_id=w.project_id,
            category=w.category,
            topic=w.topic,
            severity=w.severity,
            original_prompt=w.question_prompt,
            feedback=w.feedback,
            created_at=w.created_at,
        )
        for w in weaknesses
    ]
    return EligibleWeaknessesResponse(
        total_eligible=len(items),
        weaknesses=items,
    )


async def create_targeted_retest_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    weakness_ids: Optional[List[uuid.UUID]] = None,
    category: Optional[str] = None,
    max_questions: int = 3,
) -> TargetedRetestSessionResponse:
    """Create a targeted re-test session focusing on candidate weaknesses."""
    stmt = select(CandidateWeakness).where(
        CandidateWeakness.user_id == user_id,
        CandidateWeakness.resolved.is_(False),
    )
    if weakness_ids:
        stmt = stmt.where(CandidateWeakness.id.in_(weakness_ids))
    elif project_id:
        stmt = stmt.where(CandidateWeakness.project_id == project_id)
    if category:
        stmt = stmt.where(CandidateWeakness.category == category.strip().lower()[:64])

    clamped_limit = max(1, min(10, max_questions))
    stmt = stmt.order_by(desc(CandidateWeakness.created_at)).limit(clamped_limit)
    res = await session.execute(stmt)
    weaknesses = list(res.scalars().all())

    session_id = f"retest-{uuid.uuid4().hex[:12]}"
    questions: List[RetestQuestion] = []

    for w in weaknesses:
        q_id = f"q-{uuid.uuid4().hex[:8]}"
        q_data = await generate_targeted_retest_question(
            category=w.category,
            topic=w.topic,
            severity=w.severity,
            original_prompt=w.question_prompt,
            feedback=w.feedback,
            candidate_prior_response=w.candidate_response,
        )

        retest_q = RetestQuestion(
            question_id=q_id,
            weakness_id=w.id,
            category=w.category,
            topic=w.topic,
            severity=w.severity,
            original_prompt=w.question_prompt,
            question_text=q_data["question_text"],
            architectural_constraint=q_data["architectural_constraint"],
            evaluation_rubric=q_data["evaluation_rubric"],
        )
        questions.append(retest_q)

        # Cache question metadata for subsequent evaluation
        _ACTIVE_RETEST_QUESTIONS[q_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "weakness_id": w.id,
            "category": w.category,
            "topic": w.topic,
            "question_text": q_data["question_text"],
            "constraint": q_data["architectural_constraint"],
            "rubric": q_data["evaluation_rubric"],
        }

    return TargetedRetestSessionResponse(
        session_id=session_id,
        user_id=user_id,
        project_id=project_id,
        total_questions=len(questions),
        questions=questions,
        created_at=datetime.now(timezone.utc),
    )


async def evaluate_retest_answer(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: str,
    question_id: str,
    weakness_id: uuid.UUID,
    candidate_response: str,
) -> RetestEvaluationResponse:
    """Evaluate candidate defense, resolve weakness on pass, and update skill proficiency."""
    # 1. Fetch weakness ensuring multi-tenant IDOR ownership
    w_stmt = select(CandidateWeakness).where(
        CandidateWeakness.id == weakness_id,
        CandidateWeakness.user_id == user_id,
    )
    w_res = await session.execute(w_stmt)
    weakness = w_res.scalar_one_or_none()
    if not weakness:
        raise ValueError("Weakness record not found or does not belong to the authenticated user")

    # 2. Retrieve question metadata from cache or construct fallback
    cached = _ACTIVE_RETEST_QUESTIONS.get(question_id)
    if cached and cached.get("user_id") == user_id:
        category = cached["category"]
        topic = cached["topic"]
        q_text = cached["question_text"]
        constraint = cached["constraint"]
        rubric = cached["rubric"]
    else:
        category = weakness.category
        topic = weakness.topic
        fallback = get_fallback_retest_question(category, topic)
        q_text = fallback["question_text"]
        constraint = fallback["architectural_constraint"]
        rubric = fallback["evaluation_rubric"]

    # 3. Evaluate response
    eval_result = await evaluate_targeted_retest_defense(
        category=category,
        topic=topic,
        retest_question=q_text,
        constraint=constraint,
        rubric=rubric,
        candidate_response=candidate_response,
    )

    passed = eval_result["passed"]
    score = eval_result["score"]
    feedback = eval_result["feedback"]
    key_improvements = eval_result["key_improvements"]
    remaining_gaps = eval_result["remaining_gaps"]

    weakness_resolved = False
    updated_proficiency: Optional[float] = None

    # 4. If passed, mark weakness resolved and boost skill proficiency
    if passed:
        resolved_w = await resolve_weakness(
            session=session,
            weakness_id=weakness_id,
            user_id=user_id,
            feedback=f"Passed Targeted Re-Test [Score: {score}/100]: {feedback}",
        )
        if resolved_w is not None:
            weakness_resolved = resolved_w.resolved

    # 5. Query updated proficiency score for response
    skill_stmt = select(UserSkill).where(
        UserSkill.user_id == user_id,
        UserSkill.category == category,
        UserSkill.topic == topic,
    )
    skill_res = await session.execute(skill_stmt)
    skill = skill_res.scalar_one_or_none()
    if skill is not None:
        updated_proficiency = skill.proficiency_score

    # Commit transaction to ensure weakness resolution and skill update persist
    await session.commit()

    return RetestEvaluationResponse(
        question_id=question_id,
        weakness_id=weakness_id,
        passed=passed,
        score=score,
        feedback=feedback,
        key_improvements=key_improvements,
        remaining_gaps=remaining_gaps,
        weakness_resolved=weakness_resolved,
        updated_proficiency=updated_proficiency,
    )
