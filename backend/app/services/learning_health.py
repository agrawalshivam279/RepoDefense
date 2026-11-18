"""
Operational health and readiness inspection service for the Phase 4 Learning Loop.
Audits database model tables, senior benchmark profile catalog, mentor fallbacks, and
re-test caches.
"""

import math
from typing import Any

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

REQUIRED_BENCHMARK_DOMAINS = {
    "system_architecture",
    "database_design",
    "concurrency_performance",
    "security_isolation",
    "reliability_observability",
    "api_contract_design",
}


def _format_tier(t: Any) -> str:
    return t.value if isinstance(t, TargetRoleBenchmark) else str(t)


def _is_valid_target(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    if isinstance(val, float):
        return math.isfinite(val) and 0.0 <= val <= 100.0
    return 0 <= val <= 100


def _is_valid_weight(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    if isinstance(val, float):
        return math.isfinite(val) and 0.0 < val <= 5.0
    return 0 < val <= 5


async def _count_table(db: AsyncSession, model: Any) -> tuple[int, bool, str | None]:
    name = getattr(model, "__name__", "Table")
    try:
        res = await db.execute(select(func.count()).select_from(model))
        return int(res.scalar() or 0), True, None
    except Exception as exc:
        logger.error(f"learning_health_{name.lower()}_error", error=str(exc))
        try:
            await db.rollback()
        except Exception:
            pass
        return 0, False, f"{name} table inaccessible"


async def inspect_database_models_health(db: AsyncSession) -> DatabaseModelsHealth:
    """Inspects accessibility and record counts for UserSkill and CandidateWeakness tables."""
    skill_count, skill_ok, skill_err = await _count_table(db, UserSkill)
    weak_count, weak_ok, weak_err = await _count_table(db, CandidateWeakness)
    errors = [e for e in (skill_err, weak_err) if e]

    if skill_ok and weak_ok:
        return DatabaseModelsHealth(
            status=ComponentHealthStatus.HEALTHY,
            user_skills_accessible=True,
            candidate_weaknesses_accessible=True,
            total_user_skills=skill_count,
            total_candidate_weaknesses=weak_count,
            detail=None,
        )

    if skill_ok or weak_ok:
        return DatabaseModelsHealth(
            status=ComponentHealthStatus.DEGRADED,
            user_skills_accessible=skill_ok,
            candidate_weaknesses_accessible=weak_ok,
            total_user_skills=skill_count,
            total_candidate_weaknesses=weak_count,
            detail="; ".join(errors),
        )

    return DatabaseModelsHealth(
        status=ComponentHealthStatus.UNHEALTHY,
        user_skills_accessible=False,
        candidate_weaknesses_accessible=False,
        total_user_skills=0,
        total_candidate_weaknesses=0,
        detail="Database query failed",
    )


def inspect_benchmark_profiles_health() -> BenchmarkProfilesHealth:
    """Validates presence and schema integrity of senior benchmark tiers and domain categories."""
    invalid_keys = [
        k for k in BENCHMARK_PROFILES.keys() if not isinstance(k, TargetRoleBenchmark)
    ]
    if invalid_keys:
        return BenchmarkProfilesHealth(
            status=ComponentHealthStatus.DEGRADED,
            configured_tiers=[_format_tier(k) for k in BENCHMARK_PROFILES.keys()],
            total_categories=0,
            tier_integrity_verified=False,
            detail=f"Unsupported benchmark tier key(s): {[str(k) for k in invalid_keys]}",
        )

    required_tiers = {
        TargetRoleBenchmark.MID_LEVEL,
        TargetRoleBenchmark.SENIOR_ENGINEER,
        TargetRoleBenchmark.STAFF_PRINCIPAL,
    }

    missing_tiers = required_tiers - set(BENCHMARK_PROFILES.keys())
    if missing_tiers:
        return BenchmarkProfilesHealth(
            status=ComponentHealthStatus.DEGRADED,
            configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
            total_categories=0,
            tier_integrity_verified=False,
            detail=f"Missing required benchmark tiers: {[t.value for t in missing_tiers]}",
        )

    categories_per_tier: list[int] = []
    for tier, domains in BENCHMARK_PROFILES.items():
        if not isinstance(domains, dict):
            return BenchmarkProfilesHealth(
                status=ComponentHealthStatus.DEGRADED,
                configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
                total_categories=0,
                tier_integrity_verified=False,
                detail=f"Tier '{tier.value}' configuration must be a dictionary",
            )
        if set(domains.keys()) != REQUIRED_BENCHMARK_DOMAINS:
            diff = set(domains.keys()) ^ REQUIRED_BENCHMARK_DOMAINS
            return BenchmarkProfilesHealth(
                status=ComponentHealthStatus.DEGRADED,
                configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
                total_categories=len(domains),
                tier_integrity_verified=False,
                detail=f"Domain mismatch in tier '{tier.value}': {sorted(diff, key=str)}",
            )
        categories_per_tier.append(len(domains))
        for domain, meta in domains.items():
            if not isinstance(meta, dict):
                return BenchmarkProfilesHealth(
                    status=ComponentHealthStatus.DEGRADED,
                    configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
                    total_categories=len(domains),
                    tier_integrity_verified=False,
                    detail=f"Domain '{domain}' metadata must be a dictionary",
                )
            target = meta.get("target")
            weight = meta.get("weight")
            if not _is_valid_target(target) or not _is_valid_weight(weight):
                return BenchmarkProfilesHealth(
                    status=ComponentHealthStatus.DEGRADED,
                    configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
                    total_categories=len(domains),
                    tier_integrity_verified=False,
                    detail=f"Invalid target/weight in tier '{tier.value}' for domain '{domain}'",
                )

    if len(set(categories_per_tier)) > 1:
        return BenchmarkProfilesHealth(
            status=ComponentHealthStatus.DEGRADED,
            configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
            total_categories=0,
            tier_integrity_verified=False,
            detail=f"Inconsistent domain counts across tiers: {categories_per_tier}",
        )

    total_cats = categories_per_tier[0] if categories_per_tier else 0
    return BenchmarkProfilesHealth(
        status=ComponentHealthStatus.HEALTHY,
        configured_tiers=[_format_tier(t) for t in BENCHMARK_PROFILES.keys()],
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
            detail="Fallback synthesis error",
        )


def inspect_retest_service_health() -> RetestServiceHealth:
    """Verifies bounded question cache initialization and capacity bounds."""
    cached_count = len(_ACTIVE_RETEST_QUESTIONS)
    is_over_capacity = cached_count > _MAX_CACHED_QUESTIONS
    status = (
        ComponentHealthStatus.DEGRADED
        if is_over_capacity
        else ComponentHealthStatus.HEALTHY
    )
    detail = (
        f"Cache entries ({cached_count}) exceed capacity ({_MAX_CACHED_QUESTIONS})"
        if is_over_capacity
        else None
    )
    return RetestServiceHealth(
        status=status,
        cache_active=True,
        cached_question_count=cached_count,
        max_cache_capacity=_MAX_CACHED_QUESTIONS,
        detail=detail,
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
