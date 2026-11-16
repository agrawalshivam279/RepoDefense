"""Domain service for candidate weakness extraction and skill tracking."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.embeddings import generate_embeddings
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.skill import (
    CandidateWeaknessResponse,
    UserSkillResponse,
    UserSkillsOverviewResponse,
    WeaknessSeverity,
)

logger = structlog.get_logger(__name__)

_SEVERITY_ORDER = {
    WeaknessSeverity.CRITICAL.value: 0,
    WeaknessSeverity.MAJOR.value: 1,
    WeaknessSeverity.MINOR.value: 2,
}


def _derive_severity(score: float) -> WeaknessSeverity:
    """Derive weakness severity tier from quantitative evaluation score."""
    if score < 35.0:
        return WeaknessSeverity.CRITICAL
    if score < 65.0:
        return WeaknessSeverity.MAJOR
    return WeaknessSeverity.MINOR


async def record_evaluation_turn(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    simulation_mode: str,
    category: str,
    topic: str,
    question_prompt: str,
    feedback: str,
    passed: bool,
    score: float = 50.0,
    session_id: Optional[str] = None,
    candidate_response: Optional[str] = None,
    severity: Optional[WeaknessSeverity] = None,
) -> Tuple[UserSkill, Optional[CandidateWeakness]]:
    """Record evaluation outcome, update candidate skill proficiency, and extract weaknesses."""
    clean_cat = category.strip().lower()[:64]
    clean_topic = topic.strip().lower()[:128]
    clean_mode = simulation_mode.strip()[:32]
    clean_sid = session_id[:64] if session_id else None
    clamped_score = max(0.0, min(100.0, float(score)))

    # 1. Update or create UserSkill with pessimistic lock for atomic counter/score updates
    skill_stmt = (
        select(UserSkill)
        .where(
            UserSkill.user_id == user_id,
            UserSkill.category == clean_cat,
            UserSkill.topic == clean_topic,
        )
        .with_for_update()
    )
    skill_res = await session.execute(skill_stmt)
    skill = skill_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if skill is None:
        skill = UserSkill(
            user_id=user_id,
            category=clean_cat,
            topic=clean_topic,
            proficiency_score=round(clamped_score, 1),
            total_evaluations=1,
            passed_evaluations=1 if passed else 0,
            failed_evaluations=0 if passed else 1,
            last_evaluated_at=now,
        )
        session.add(skill)
    else:
        skill.total_evaluations += 1
        if passed:
            skill.passed_evaluations += 1
        else:
            skill.failed_evaluations += 1
        # Weighted moving average: 70% prior proficiency, 30% new turn score
        new_score = skill.proficiency_score * 0.7 + clamped_score * 0.3
        skill.proficiency_score = round(max(0.0, min(100.0, new_score)), 1)
        skill.last_evaluated_at = now

    weakness: Optional[CandidateWeakness] = None

    # 2. Extract CandidateWeakness on failed evaluations
    if not passed:
        chosen_severity = severity or _derive_severity(clamped_score)
        sev_value = (
            chosen_severity.value
            if isinstance(chosen_severity, WeaknessSeverity)
            else str(chosen_severity)
        )

        embedding_vector: Optional[List[float]] = None
        try:
            # Offload CPU-bound embedding inference to worker thread pool
            embeddings = await asyncio.to_thread(
                generate_embeddings, [f"{clean_cat}: {clean_topic}"]
            )
            if embeddings and len(embeddings[0]) == 384:
                embedding_vector = embeddings[0]
        except Exception as exc:
            logger.warning("weakness_embedding_generation_failed", error=str(exc))

        weakness = CandidateWeakness(
            user_id=user_id,
            project_id=project_id,
            simulation_mode=clean_mode,
            session_id=clean_sid,
            category=clean_cat,
            topic=clean_topic,
            severity=sev_value,
            question_prompt=question_prompt,
            candidate_response=candidate_response,
            feedback=feedback,
            resolved=False,
            topic_embedding=embedding_vector,
        )
        session.add(weakness)

    await session.flush()
    return skill, weakness


async def resolve_weakness(
    session: AsyncSession,
    weakness_id: uuid.UUID,
    user_id: uuid.UUID,
    feedback: Optional[str] = None,
) -> Optional[CandidateWeakness]:
    """Mark an identified weakness as resolved, append mentor notes, and boost skill score."""
    stmt = (
        select(CandidateWeakness)
        .where(
            CandidateWeakness.id == weakness_id,
            CandidateWeakness.user_id == user_id,
        )
        .with_for_update()
    )
    res = await session.execute(stmt)
    weakness = res.scalar_one_or_none()
    if weakness is None:
        return None

    now = datetime.now(timezone.utc)
    # Only reinforce skill on first transition from unresolved to resolved
    if not weakness.resolved:
        weakness.resolved = True
        weakness.resolved_at = now

        # Reinforce associated skill proficiency and update counters consistently
        skill_stmt = (
            select(UserSkill)
            .where(
                UserSkill.user_id == user_id,
                UserSkill.category == weakness.category,
                UserSkill.topic == weakness.topic,
            )
            .with_for_update()
        )
        skill_res = await session.execute(skill_stmt)
        skill = skill_res.scalar_one_or_none()
        if skill is not None:
            skill.proficiency_score = min(100.0, round(skill.proficiency_score + 10.0, 1))
            skill.total_evaluations += 1
            skill.passed_evaluations += 1
            skill.last_evaluated_at = now

    if feedback:
        weakness.feedback = f"{weakness.feedback}\n\n[Resolution Note]: {feedback}".strip()

    await session.flush()
    return weakness


async def get_candidate_weaknesses(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    resolved: Optional[bool] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[CandidateWeakness]:
    """Retrieve filtered weaknesses for the authenticated candidate."""
    stmt = select(CandidateWeakness).where(CandidateWeakness.user_id == user_id)
    if project_id is not None:
        stmt = stmt.where(CandidateWeakness.project_id == project_id)
    if resolved is not None:
        stmt = stmt.where(CandidateWeakness.resolved == resolved)
    if category is not None:
        stmt = stmt.where(CandidateWeakness.category == category.strip().lower()[:64])

    safe_limit = min(100, max(1, limit))
    stmt = stmt.order_by(desc(CandidateWeakness.created_at)).limit(safe_limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_user_skills_overview(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> UserSkillsOverviewResponse:
    """Compute aggregated portfolio summary across candidate proficiencies and gaps."""
    # 1. Fetch all candidate skills
    skills_stmt = (
        select(UserSkill)
        .where(UserSkill.user_id == user_id)
        .order_by(UserSkill.proficiency_score.asc())
    )
    skills = list((await session.execute(skills_stmt)).scalars().all())

    # 2. Fetch unresolved weaknesses
    unresolved_stmt = (
        select(CandidateWeakness)
        .where(CandidateWeakness.user_id == user_id, CandidateWeakness.resolved.is_(False))
        .order_by(desc(CandidateWeakness.created_at))
    )
    unresolved = list((await session.execute(unresolved_stmt)).scalars().all())

    # 3. Count resolved weaknesses
    resolved_stmt = select(func.count(CandidateWeakness.id)).where(
        CandidateWeakness.user_id == user_id,
        CandidateWeakness.resolved.is_(True),
    )
    resolved_count = (await session.execute(resolved_stmt)).scalar() or 0

    # 4. Compute metrics
    total_skills = len(skills)
    avg_score = (
        round(sum(s.proficiency_score for s in skills) / total_skills, 1)
        if total_skills > 0
        else 0.0
    )
    weak_count = sum(1 for s in skills if s.proficiency_score < 70.0)
    strong_count = sum(1 for s in skills if s.proficiency_score >= 70.0)

    # Sort unresolved weaknesses by severity priority (critical -> major -> minor)
    sorted_unresolved = sorted(
        unresolved,
        key=lambda w: (
            _SEVERITY_ORDER.get(w.severity, 3),
            -(w.created_at.timestamp() if w.created_at else 0.0),
        ),
    )

    top_weaknesses = [
        CandidateWeaknessResponse.model_validate(w) for w in sorted_unresolved[:5]
    ]
    skill_responses = [UserSkillResponse.model_validate(s) for s in skills]

    return UserSkillsOverviewResponse(
        user_id=user_id,
        total_skills_tracked=total_skills,
        avg_proficiency_pct=avg_score,
        weak_skills_count=weak_count,
        strong_skills_count=strong_count,
        unresolved_weaknesses_count=len(unresolved),
        resolved_weaknesses_count=resolved_count,
        top_weaknesses=top_weaknesses,
        skills=skill_responses,
    )
