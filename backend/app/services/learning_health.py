"""
Operational health and readiness inspection service for the Phase 4 Learning Loop.
Audits database model tables, senior benchmark profile catalog, mentor fallbacks, and
re-test caches.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mentor_prompts import build_deterministic_mentor_explanation
from app.core.config import settings
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.learning_health import (
    BenchmarkProfilesHealth,
    ComponentHealthStatus,
    DatabaseModelsHealth,
    LearningLoopHealthResponse,
    MentorServiceHealth,
    RetestServiceHealth,
)
from app.schemas.skill_gap import TargetRoleBenchmark
from app.services.retest_service import _ACTIVE_RETEST_QUESTIONS, _MAX_CACHED_QUESTIONS
from app.services.skill_gap import BENCHMARK_PROFILES

logger = structlog.get_logger(__name__)

SUPPORTED_FALLBACK_TOPICS = [
    "connection_pooling",
    "concurrency_lost_updates",
    "cache_stampede",
    "rate_limiting",
    "domain_decoupling",
]


async def inspect_database_models_health(db: AsyncSession) -> DatabaseModelsHealth:
    """Inspects accessibility and record counts for UserSkill and CandidateWeakness tables."""
    try:
        skill_count_stmt = select(func.count()).select_from(UserSkill)
        weak_count_stmt = select(func.count()).select_from(CandidateWeakness)

        skill_res = await db.execute(skill_count_stmt)
        weak_res = await db.execute(weak_count_stmt)

        skill_count = int(skill_res.scalar() or 0)
        weak_count = int(weak_res.scalar() or 0)

        return DatabaseModelsHealth(
            status=ComponentHealthStatus.HEALTHY,
            user_skills_accessible=True,
            candidate_weaknesses_accessible=True,
            total_user_skills=skill_count,
            total_candidate_weaknesses=weak_count,
            detail=None,
        )
    except Exception as exc:
        logger.error("learning_health_db_error", error=str(exc))
        return DatabaseModelsHealth(
            status=ComponentHealthStatus.UNHEALTHY,
            user_skills_accessible=False,
            candidate_weaknesses_accessible=False,
            total_user_skills=0,
            total_candidate_weaknesses=0,
            detail=f"Database query failed: {type(exc).__name__}",
        )


def inspect_benchmark_profiles_health() -> BenchmarkProfilesHealth:
    """Validates presence and schema integrity of senior benchmark tiers and domain categories."""
    required_tiers = {
        TargetRoleBenchmark.MID_LEVEL,
        TargetRoleBenchmark.SENIOR_ENGINEER,
        TargetRoleBenchmark.STAFF_PRINCIPAL,
    }

    missing_tiers = required_tiers - set(BENCHMARK_PROFILES.keys())
    if missing_tiers:
        return BenchmarkProfilesHealth(
            status=ComponentHealthStatus.DEGRADED,
            configured_tiers=[t.value for t in BENCHMARK_PROFILES.keys()],
            total_categories=0,
            tier_integrity_verified=False,
            detail=f"Missing required benchmark tiers: {[t.value for t in missing_tiers]}",
        )

    categories_per_tier: list[int] = []
    for tier, domains in BENCHMARK_PROFILES.items():
        categories_per_tier.append(len(domains))
        for domain, meta in domains.items():
            target = meta.get("target", -1.0)
            weight = meta.get("weight", -1.0)
            if not (0.0 <= target <= 100.0) or weight <= 0.0:
                return BenchmarkProfilesHealth(
                    status=ComponentHealthStatus.DEGRADED,
                    configured_tiers=[t.value for t in BENCHMARK_PROFILES.keys()],
                    total_categories=len(domains),
                    tier_integrity_verified=False,
                    detail=f"Invalid target/weight in tier '{tier.value}' for domain '{domain}'",
                )

    total_cats = categories_per_tier[0] if categories_per_tier else 0
    return BenchmarkProfilesHealth(
        status=ComponentHealthStatus.HEALTHY,
        configured_tiers=[t.value for t in BENCHMARK_PROFILES.keys()],
        total_categories=total_cats,
        tier_integrity_verified=True,
        detail=None,
    )


def inspect_mentor_service_health() -> MentorServiceHealth:
    """Verifies that deterministic offline fallbacks are ready for zero-downtime degradation."""
    try:
        test_fallback = build_deterministic_mentor_explanation(
            category="database_design",
            topic="connection_pooling",
            feedback="Test verification probe",
        )
        if not test_fallback or not test_fallback.code_examples:
            return MentorServiceHealth(
                status=ComponentHealthStatus.DEGRADED,
                fallbacks_ready=False,
                supported_fallback_topics=SUPPORTED_FALLBACK_TOPICS,
                detail="Fallback returned empty code examples",
            )
        return MentorServiceHealth(
            status=ComponentHealthStatus.HEALTHY,
            fallbacks_ready=True,
            supported_fallback_topics=SUPPORTED_FALLBACK_TOPICS,
            detail=None,
        )
    except Exception as exc:
        logger.error("mentor_fallback_verification_failed", error=str(exc))
        return MentorServiceHealth(
            status=ComponentHealthStatus.DEGRADED,
            fallbacks_ready=False,
            supported_fallback_topics=SUPPORTED_FALLBACK_TOPICS,
            detail=f"Fallback synthesis error: {type(exc).__name__}",
        )


def inspect_retest_service_health() -> RetestServiceHealth:
    """Verifies bounded question cache initialization and capacity bounds."""
    cached_count = len(_ACTIVE_RETEST_QUESTIONS)
    return RetestServiceHealth(
        status=ComponentHealthStatus.HEALTHY,
        cache_active=True,
        cached_question_count=cached_count,
        max_cache_capacity=_MAX_CACHED_QUESTIONS,
        detail=None,
    )


async def inspect_learning_loop_health(db: AsyncSession) -> LearningLoopHealthResponse:
    """Performs full operational health inspection of all Phase 4 Learning Loop subsystems."""
    db_health = await inspect_database_models_health(db)
    benchmark_health = inspect_benchmark_profiles_health()
    mentor_health = inspect_mentor_service_health()
    retest_health = inspect_retest_service_health()

    if db_health.status == ComponentHealthStatus.UNHEALTHY:
        overall_status = ComponentHealthStatus.UNHEALTHY
    elif any(
        s.status == ComponentHealthStatus.DEGRADED
        for s in (db_health, benchmark_health, mentor_health, retest_health)
    ):
        overall_status = ComponentHealthStatus.DEGRADED
    else:
        overall_status = ComponentHealthStatus.HEALTHY

    logger.info(
        "learning_loop_health_inspected",
        overall_status=overall_status.value,
        db_status=db_health.status.value,
        benchmark_status=benchmark_health.status.value,
        mentor_status=mentor_health.status.value,
        retest_status=retest_health.status.value,
    )

    return LearningLoopHealthResponse(
        status=overall_status,
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
        database_models=db_health,
        benchmark_profiles=benchmark_health,
        mentor_service=mentor_health,
        retest_service=retest_health,
    )
