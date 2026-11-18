"""
Skill Gap Analysis service for RepoDefense.
Compares candidate competencies against Senior and Principal Engineer benchmarks.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.skill_gap import (
    CategoryGapMetric,
    GapStatus,
    RemediationPriority,
    RemediationRecommendation,
    SkillGapAnalysisResponse,
    TargetRoleBenchmark,
)

logger = structlog.get_logger(__name__)

BENCHMARK_PROFILES: dict[TargetRoleBenchmark, dict[str, dict[str, float]]] = {
    TargetRoleBenchmark.MID_LEVEL: {
        "system_architecture": {"target": 65.0, "weight": 1.2},
        "database_design": {"target": 65.0, "weight": 1.0},
        "concurrency_performance": {"target": 60.0, "weight": 1.0},
        "security_isolation": {"target": 65.0, "weight": 1.1},
        "reliability_observability": {"target": 60.0, "weight": 0.9},
        "api_contract_design": {"target": 70.0, "weight": 0.8},
    },
    TargetRoleBenchmark.SENIOR_ENGINEER: {
        "system_architecture": {"target": 85.0, "weight": 1.2},
        "database_design": {"target": 80.0, "weight": 1.0},
        "concurrency_performance": {"target": 80.0, "weight": 1.1},
        "security_isolation": {"target": 85.0, "weight": 1.1},
        "reliability_observability": {"target": 75.0, "weight": 0.9},
        "api_contract_design": {"target": 80.0, "weight": 0.8},
    },
    TargetRoleBenchmark.STAFF_PRINCIPAL: {
        "system_architecture": {"target": 92.0, "weight": 1.3},
        "database_design": {"target": 88.0, "weight": 1.0},
        "concurrency_performance": {"target": 90.0, "weight": 1.2},
        "security_isolation": {"target": 92.0, "weight": 1.2},
        "reliability_observability": {"target": 88.0, "weight": 1.0},
        "api_contract_design": {"target": 88.0, "weight": 0.8},
    },
}


class SkillGapService:
    """Computes technical skill deficits relative to engineering benchmarks."""

    @staticmethod
    def _calculate_gap_status(current: float, target: float, deficit: float) -> GapStatus:
        if current >= target + 5.0:
            return GapStatus.SURPASSED
        if deficit <= 5.0:
            return GapStatus.MET
        if deficit <= 20.0:
            return GapStatus.MODERATE_GAP
        return GapStatus.CRITICAL_GAP

    @staticmethod
    def _estimate_percentile(current: float, target: float) -> float:
        ratio = current / max(target, 1.0)
        est = ratio * 75.0
        return round(min(99.0, max(5.0, est)), 1)

    async def analyze_skill_gaps(
        self,
        db: AsyncSession,
        user_id: UUID,
        target_role: TargetRoleBenchmark = TargetRoleBenchmark.SENIOR_ENGINEER,
        project_id: UUID | None = None,
    ) -> SkillGapAnalysisResponse:
        """Run complete comparative gap analysis against target seniority tier."""
        default_bench = BENCHMARK_PROFILES[TargetRoleBenchmark.SENIOR_ENGINEER]
        profile = BENCHMARK_PROFILES.get(target_role, default_bench)

        # 1. Fetch user skills
        skill_stmt = select(UserSkill).where(UserSkill.user_id == user_id)
        skill_res = await db.execute(skill_stmt)
        user_skills = skill_res.scalars().all()

        category_scores: dict[str, list[float]] = {}
        for s in user_skills:
            cat = s.category.lower()
            category_scores.setdefault(cat, []).append(float(s.proficiency_score))

        # 2. Fetch active candidate weaknesses
        weak_stmt = select(CandidateWeakness).where(
            CandidateWeakness.user_id == user_id,
            CandidateWeakness.resolved.is_(False),
        )
        if project_id:
            weak_stmt = weak_stmt.where(CandidateWeakness.project_id == project_id)
        weak_res = await db.execute(weak_stmt)
        unresolved_weaknesses = weak_res.scalars().all()

        # 3. Compute category metrics
        categories: list[CategoryGapMetric] = []
        for cat_name, bench_meta in profile.items():
            scores = category_scores.get(cat_name, [])
            current_score = round(sum(scores) / len(scores), 1) if scores else 0.0
            target_score = bench_meta["target"]
            deficit = round(max(0.0, target_score - current_score), 1)
            status = self._calculate_gap_status(current_score, target_score, deficit)
            percentile = self._estimate_percentile(current_score, target_score)

            categories.append(
                CategoryGapMetric(
                    category=cat_name,
                    current_score=current_score,
                    benchmark_score=target_score,
                    gap_deficit=deficit,
                    status=status,
                    weight=bench_meta["weight"],
                    percentile_estimate=percentile,
                )
            )

        # 4. Overall weighted scores
        total_weight = sum(c.weight for c in categories) or 1.0
        cand_weighted_sum = sum(c.current_score * c.weight for c in categories)
        bench_weighted_sum = sum(c.benchmark_score * c.weight for c in categories)
        overall_cand = round(cand_weighted_sum / total_weight, 1)
        overall_bench = round(bench_weighted_sum / total_weight, 1)
        raw_pct = (overall_cand / max(overall_bench, 1.0)) * 100.0
        readiness_pct = min(100.0, max(0.0, round(raw_pct, 1)))

        # 5. Extract strengths and critical gaps
        strengths = [
            c.category for c in sorted(categories, key=lambda x: x.current_score, reverse=True)
            if c.status in (GapStatus.SURPASSED, GapStatus.MET)
        ]
        critical_gaps = [
            c.category for c in sorted(categories, key=lambda x: x.gap_deficit, reverse=True)
            if c.status in (GapStatus.CRITICAL_GAP, GapStatus.MODERATE_GAP)
        ]

        # 6. Build prioritized recommendations
        recs = self._build_recommendations(unresolved_weaknesses, categories)

        logger.info(
            "skill_gap_analysis_computed",
            user_id=str(user_id),
            target_role=target_role.value,
            overall_readiness=readiness_pct,
            strengths_count=len(strengths),
            gaps_count=len(critical_gaps),
        )

        return SkillGapAnalysisResponse(
            target_role=target_role,
            overall_candidate_score=overall_cand,
            overall_benchmark_score=overall_bench,
            overall_readiness_pct=readiness_pct,
            categories=categories,
            recommendations=recs,
            strengths=strengths,
            critical_gaps=critical_gaps,
            analyzed_at=datetime.now(timezone.utc),
        )

    def _build_recommendations(
        self,
        weaknesses: list[CandidateWeakness],
        categories: list[CategoryGapMetric],
    ) -> list[RemediationRecommendation]:
        """Synthesize prioritized remediation plan from weaknesses and deficits."""
        recs: list[RemediationRecommendation] = []
        topic_map: dict[str, dict[str, Any]] = {}

        for w in weaknesses:
            t = w.topic.lower()
            if t not in topic_map:
                topic_map[t] = {
                    "category": w.category.lower(),
                    "count": 0,
                    "max_sev": w.severity.lower() if hasattr(w, "severity") else "major",
                }
            topic_map[t]["count"] += 1

        for topic, data in topic_map.items():
            sev = data["max_sev"]
            priority = (
                RemediationPriority.CRITICAL if sev == "critical"
                else RemediationPriority.HIGH if sev == "major"
                else RemediationPriority.MEDIUM
            )
            title = topic.replace("_", " ").title()
            recs.append(
                RemediationRecommendation(
                    topic=title,
                    category=data["category"],
                    priority=priority,
                    rationale=f"Found {data['count']} active gap(s) identified in sessions.",
                    unresolved_weakness_count=data["count"],
                    suggested_action=f"Launch a Targeted Re-Test session focusing on {title}.",
                )
            )

        # Category-level fallbacks if few topic weaknesses exist
        for gap_cat in [c for c in categories if c.status == GapStatus.CRITICAL_GAP]:
            if not any(r.category == gap_cat.category for r in recs):
                cat_title = gap_cat.category.replace("_", " ").title()
                recs.append(
                    RemediationRecommendation(
                        topic=cat_title,
                        category=gap_cat.category,
                        priority=RemediationPriority.HIGH,
                        rationale=f"Proficiency deficit of {gap_cat.gap_deficit} pts vs benchmark.",
                        unresolved_weakness_count=0,
                        suggested_action=f"Explore Mentor Mode guides for {cat_title}.",
                    )
                )

        p_order = {
            RemediationPriority.CRITICAL: 0,
            RemediationPriority.HIGH: 1,
            RemediationPriority.MEDIUM: 2,
            RemediationPriority.LOW: 3,
        }
        recs.sort(key=lambda r: (p_order.get(r.priority, 9), -r.unresolved_weakness_count))
        return recs[:10]


skill_gap_service = SkillGapService()
