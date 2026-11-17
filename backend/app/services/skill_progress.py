"""Service layer computing candidate skill progress, velocity, and telemetry."""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.progress import (
    CategoryProgressDelta,
    ProficiencyTrendPoint,
    TopicMasteryItem,
    UserProgressOverviewResponse,
    WeaknessVelocityMetric,
)


def _to_topic_mastery(s: UserSkill) -> TopicMasteryItem:
    """Converts a UserSkill model to a TopicMasteryItem response model."""
    p_rate = (
        round((s.passed_evaluations / s.total_evaluations) * 100.0, 1)
        if s.total_evaluations > 0
        else 0.0
    )
    return TopicMasteryItem(
        topic=s.topic,
        category=s.category,
        proficiency_score=s.proficiency_score,
        evaluations=s.total_evaluations,
        pass_rate_pct=p_rate,
        last_evaluated_at=s.last_evaluated_at,
    )


def _calculate_mastery_status(proficiency: float) -> str:
    """Classifies proficiency score into standardized mastery tiers."""
    if proficiency >= 80.0:
        return "mastered"
    if proficiency >= 65.0:
        return "proficient"
    if proficiency >= 50.0:
        return "improving"
    return "needs_focus"


def _calculate_learning_streak(activity_dates: Set[datetime.date]) -> int:
    """Calculates consecutive active days ending either today or yesterday."""
    if not activity_dates:
        return 0

    sorted_dates = sorted(activity_dates, reverse=True)
    today = datetime.now(timezone.utc).date()
    current_check = sorted_dates[0]

    # If the most recent active date is older than yesterday, streak is broken
    delta_from_today = (today - current_check).days
    if delta_from_today > 1:
        return 0

    streak = 1
    for i in range(1, len(sorted_dates)):
        prev_date = sorted_dates[i]
        diff = (current_check - prev_date).days
        if diff == 1:
            streak += 1
            current_check = prev_date
        elif diff == 0:
            continue
        else:
            break
    return streak


async def get_user_progress_overview(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> UserProgressOverviewResponse:
    """Aggregates unified skill progress, velocity metrics, category deltas, and streak."""
    # Query user skills
    skills_stmt = (
        select(UserSkill)
        .where(UserSkill.user_id == user_id)
        .order_by(UserSkill.proficiency_score.desc())
    )
    skills_res = await session.execute(skills_stmt)
    skills = list(skills_res.scalars().all())

    # Query candidate weaknesses
    weakness_stmt = (
        select(CandidateWeakness)
        .where(CandidateWeakness.user_id == user_id)
        .order_by(CandidateWeakness.created_at.asc())
    )
    weakness_res = await session.execute(weakness_stmt)
    weaknesses = list(weakness_res.scalars().all())

    # 1. Overall Skill Metrics
    total_evals = sum(s.total_evaluations for s in skills)
    total_passed = sum(s.passed_evaluations for s in skills)
    overall_pass_rate = (
        round((total_passed / total_evals) * 100.0, 1) if total_evals > 0 else 0.0
    )
    overall_proficiency = (
        round(sum(s.proficiency_score for s in skills) / len(skills), 1)
        if skills
        else 0.0
    )
    mastered_count = sum(1 for s in skills if s.proficiency_score >= 80.0)

    # 2. Weakness Velocity
    total_weaknesses = len(weaknesses)
    resolved_weaknesses = sum(1 for w in weaknesses if w.resolved)
    resolution_rate = (
        round((resolved_weaknesses / total_weaknesses) * 100.0, 1)
        if total_weaknesses > 0
        else 0.0
    )

    sev_counts: Dict[str, Dict[str, int]] = {
        "critical": {"total": 0, "resolved": 0},
        "major": {"total": 0, "resolved": 0},
        "minor": {"total": 0, "resolved": 0},
    }
    resolution_durations: List[float] = []

    activity_dates: Set[datetime.date] = set()

    for w in weaknesses:
        s_tier = w.severity.lower() if w.severity else "major"
        if s_tier in sev_counts:
            sev_counts[s_tier]["total"] += 1
            if w.resolved:
                sev_counts[s_tier]["resolved"] += 1

        if w.created_at:
            activity_dates.add(w.created_at.date())

        if w.resolved and w.resolved_at and w.created_at:
            activity_dates.add(w.resolved_at.date())
            duration_hours = (w.resolved_at - w.created_at).total_seconds() / 3600.0
            if duration_hours >= 0.0:
                resolution_durations.append(duration_hours)

    avg_resolution_hours = (
        round(sum(resolution_durations) / len(resolution_durations), 1)
        if resolution_durations
        else None
    )

    velocity_metric = WeaknessVelocityMetric(
        total_identified=total_weaknesses,
        total_resolved=resolved_weaknesses,
        resolution_rate_pct=resolution_rate,
        critical_resolved=sev_counts["critical"]["resolved"],
        critical_total=sev_counts["critical"]["total"],
        major_resolved=sev_counts["major"]["resolved"],
        major_total=sev_counts["major"]["total"],
        minor_resolved=sev_counts["minor"]["resolved"],
        minor_total=sev_counts["minor"]["total"],
        average_resolution_hours=avg_resolution_hours,
    )

    # 3. Category Progress Deltas
    cat_skills: Dict[str, List[UserSkill]] = defaultdict(list)
    for s in skills:
        cat_skills[s.category].append(s)
        for ts in (s.last_evaluated_at, s.updated_at, s.created_at):
            if ts:
                activity_dates.add(ts.date())

    cat_weaknesses: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "resolved": 0})
    for w in weaknesses:
        cat_weaknesses[w.category]["total"] += 1
        if w.resolved:
            cat_weaknesses[w.category]["resolved"] += 1

    all_categories = sorted(set(list(cat_skills.keys()) + list(cat_weaknesses.keys())))
    category_deltas: List[CategoryProgressDelta] = []

    for cat in all_categories:
        c_skills = cat_skills.get(cat, [])
        c_evals = sum(s.total_evaluations for s in c_skills)
        c_passed = sum(s.passed_evaluations for s in c_skills)
        c_pass_rate = round((c_passed / c_evals) * 100.0, 1) if c_evals > 0 else 0.0
        c_prof = (
            round(sum(s.proficiency_score for s in c_skills) / len(c_skills), 1)
            if c_skills
            else 50.0
        )
        c_w = cat_weaknesses.get(cat, {"total": 0, "resolved": 0})

        category_deltas.append(
            CategoryProgressDelta(
                category=cat,
                current_proficiency=c_prof,
                total_evaluations=c_evals,
                passed_evaluations=c_passed,
                pass_rate_pct=c_pass_rate,
                total_weaknesses=c_w["total"],
                resolved_weaknesses=c_w["resolved"],
                status=_calculate_mastery_status(c_prof),
            )
        )

    # 4. Learning Streak
    streak_days = _calculate_learning_streak(activity_dates)

    # 5. Timeline Buckets
    recent_timeline = await get_user_progress_timeline(session, user_id, days=30)

    # 6. Top Improved Topics vs Needs Focus Topics
    sorted_by_prof = sorted(skills, key=lambda s: s.proficiency_score, reverse=True)
    top_improved = [_to_topic_mastery(s) for s in sorted_by_prof[:5]]
    needs_focus = [
        _to_topic_mastery(s)
        for s in sorted(skills, key=lambda s: s.proficiency_score)
        if s.proficiency_score < 70.0
    ][:5]

    return UserProgressOverviewResponse(
        overall_proficiency=overall_proficiency,
        total_evaluations=total_evals,
        total_passed=total_passed,
        overall_pass_rate_pct=overall_pass_rate,
        active_skills_count=len(skills),
        mastered_skills_count=mastered_count,
        learning_streak_days=streak_days,
        weakness_velocity=velocity_metric,
        category_deltas=category_deltas,
        recent_timeline=recent_timeline,
        top_improved_topics=top_improved,
        needs_focus_topics=needs_focus,
    )


async def get_user_progress_timeline(
    session: AsyncSession,
    user_id: uuid.UUID,
    days: int = 30,
) -> List[ProficiencyTrendPoint]:
    """Generates daily timeline trend points tracking cumulative evaluations and proficiency."""
    skills_stmt = select(UserSkill).where(UserSkill.user_id == user_id)
    skills_res = await session.execute(skills_stmt)
    skills = list(skills_res.scalars().all())

    if not skills:
        return []

    # Map skills by last evaluation date or updated_at date
    date_points: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"evals": 0, "passed": 0, "total_prof": 0.0, "count": 0}
    )

    for s in skills:
        ts = s.last_evaluated_at or s.updated_at or s.created_at
        if ts:
            d_str = ts.strftime("%Y-%m-%d")
            entry = date_points[d_str]
            entry["evals"] += s.total_evaluations
            entry["passed"] += s.passed_evaluations
            entry["total_prof"] += s.proficiency_score
            entry["count"] += 1

    sorted_dates = sorted(date_points.keys())
    if days > 0:
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
        sorted_dates = [d for d in sorted_dates if d >= cutoff]

    timeline: List[ProficiencyTrendPoint] = []
    for d in sorted_dates:
        data = date_points[d]
        avg_prof = (
            round(data["total_prof"] / data["count"], 1) if data["count"] > 0 else 0.0
        )
        timeline.append(
            ProficiencyTrendPoint(
                date=d,
                average_proficiency=avg_prof,
                evaluations_count=int(data["evals"]),
                passed_count=int(data["passed"]),
            )
        )

    return timeline
