"""
Unit and API contract tests for Step 4.6a Senior Benchmark Engine & Skill Gap Aggregator.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.skill_gap import (
    CategoryGapMetric,
    GapStatus,
    RemediationPriority,
    RemediationRecommendation,
    SkillGapAnalysisResponse,
    TargetRoleBenchmark,
)
from app.services.skill_gap import (
    BENCHMARK_PROFILES,
    skill_gap_service,
)


def _make_mock_db(skills=None, weaknesses=None):
    """Build mock AsyncSession returning skills and weaknesses based on query."""
    mock_db = AsyncMock()
    s_list = skills if skills is not None else []
    w_list = weaknesses if weaknesses is not None else []

    async def _exec(stmt):
        res = MagicMock()
        if "candidate_weaknesses" in str(stmt):
            res.scalars.return_value.all.return_value = w_list
        else:
            res.scalars.return_value.all.return_value = s_list
        return res

    mock_db.execute.side_effect = _exec
    return mock_db


def _make_skill(user_id: uuid.UUID, cat: str, topic: str, score: float) -> UserSkill:
    return UserSkill(
        id=uuid.uuid4(),
        user_id=user_id,
        category=cat,
        topic=topic,
        proficiency_score=score,
        total_evaluations=1,
        passed_evaluations=1,
        failed_evaluations=0,
        last_evaluated_at=datetime.now(timezone.utc),
    )


def _make_weakness(user_id: uuid.UUID, cat: str, topic: str, sev: str) -> CandidateWeakness:
    return CandidateWeakness(
        id=uuid.uuid4(),
        user_id=user_id,
        project_id=uuid.uuid4(),
        simulation_mode="defense",
        category=cat,
        topic=topic,
        severity=sev,
        question_prompt="Prompt",
        feedback="Feedback",
        resolved=False,
    )


def test_schema_validations():
    """Verify validation boundaries and extra field forbidding."""
    metric = CategoryGapMetric(
        category="system_architecture",
        current_score=85.0,
        benchmark_score=85.0,
        gap_deficit=0.0,
        status=GapStatus.MET,
        weight=1.2,
        percentile_estimate=75.0,
    )
    assert metric.current_score == 85.0
    assert metric.status == GapStatus.MET

    with pytest.raises(ValidationError):
        CategoryGapMetric(
            category="system_architecture",
            current_score=105.0,
            benchmark_score=85.0,
            gap_deficit=0.0,
            status=GapStatus.MET,
            weight=1.2,
            percentile_estimate=75.0,
        )

    with pytest.raises(ValidationError):
        RemediationRecommendation(
            topic="Caching",
            category="concurrency_performance",
            priority=RemediationPriority.HIGH,
            rationale="1234",
            suggested_action="Review caching.",
        )


def test_benchmark_profiles():
    """Verify all defined tiers have proper targets and weights."""
    roles = [
        TargetRoleBenchmark.MID_LEVEL,
        TargetRoleBenchmark.SENIOR_ENGINEER,
        TargetRoleBenchmark.STAFF_PRINCIPAL,
    ]
    for role in roles:
        assert role in BENCHMARK_PROFILES
        profile = BENCHMARK_PROFILES[role]
        assert "system_architecture" in profile and "database_design" in profile
        for cat, meta in profile.items():
            assert 0.0 < meta["target"] <= 100.0 and 0.0 < meta["weight"] <= 5.0


def test_analyze_skill_gaps_empty_user():
    """Verify clean response when candidate has zero recorded skills."""
    async def _impl():
        mock_db = _make_mock_db(skills=[], weaknesses=[])
        user_id = uuid.uuid4()
        resp = await skill_gap_service.analyze_skill_gaps(
            db=mock_db,
            user_id=user_id,
            target_role=TargetRoleBenchmark.SENIOR_ENGINEER,
        )
        assert isinstance(resp, SkillGapAnalysisResponse)
        assert resp.overall_candidate_score == 0.0 and resp.overall_readiness_pct == 0.0
        assert len(resp.categories) == 6
        for c in resp.categories:
            assert c.current_score == 0.0 and c.status == GapStatus.CRITICAL_GAP
        assert len(resp.strengths) == 0 and len(resp.critical_gaps) == 6
        assert len(resp.recommendations) > 0

    asyncio.run(_impl())


def test_analyze_skill_gaps_populated_skills():
    """Verify gap calculations, percentile estimates, and weakness-driven recommendations."""
    async def _impl():
        user_id = uuid.uuid4()
        skills = [
            _make_skill(user_id, "system_architecture", "microservices", 92.0),
            _make_skill(user_id, "database_design", "indexing", 80.0),
            _make_skill(user_id, "concurrency_performance", "race_conditions", 60.0),
        ]
        weaknesses = [
            _make_weakness(user_id, "concurrency_performance", "race_conditions", "critical"),
        ]
        mock_db = _make_mock_db(skills=skills, weaknesses=weaknesses)
        resp = await skill_gap_service.analyze_skill_gaps(
            db=mock_db,
            user_id=user_id,
            target_role=TargetRoleBenchmark.SENIOR_ENGINEER,
        )
        assert resp.overall_candidate_score > 0.0 and resp.overall_readiness_pct > 0.0

        sys_arch = next(c for c in resp.categories if c.category == "system_architecture")
        assert sys_arch.current_score == 92.0 and sys_arch.status == GapStatus.SURPASSED
        assert "system_architecture" in resp.strengths

        db_design = next(c for c in resp.categories if c.category == "database_design")
        assert db_design.current_score == 80.0 and db_design.status == GapStatus.MET

        concur = next(c for c in resp.categories if c.category == "concurrency_performance")
        assert concur.current_score == 60.0 and concur.gap_deficit == 20.0
        assert concur.status == GapStatus.MODERATE_GAP

        assert len(resp.recommendations) > 0
        top_rec = resp.recommendations[0]
        assert top_rec.priority == RemediationPriority.CRITICAL
        assert top_rec.unresolved_weakness_count == 1
        assert "Race Conditions" in top_rec.topic

    asyncio.run(_impl())


def test_recommendation_grouping_and_severity_ordering():
    """Verify category isolation and severity ordering invariant to weakness row order."""
    u_id = uuid.uuid4()
    w_min = _make_weakness(u_id, "database_design", "caching", "minor")
    w_crit = _make_weakness(u_id, "database_design", "caching", "critical")
    w_conc = _make_weakness(u_id, "concurrency_performance", "caching", "major")

    recs_a = skill_gap_service._build_recommendations([w_min, w_crit, w_conc], [])
    recs_b = skill_gap_service._build_recommendations([w_crit, w_min, w_conc], [])
    assert len(recs_a) == 2 and len(recs_b) == 2

    db_a = next(r for r in recs_a if r.category == "database_design")
    db_b = next(r for r in recs_b if r.category == "database_design")
    assert db_a.priority == RemediationPriority.CRITICAL
    assert db_b.priority == RemediationPriority.CRITICAL
    assert db_a.unresolved_weakness_count == 2

    conc_r = next(r for r in recs_a if r.category == "concurrency_performance")
    assert conc_r.priority == RemediationPriority.HIGH
    assert conc_r.unresolved_weakness_count == 1


def test_api_get_skill_gap_analysis_authenticated():
    """Verify GET /api/v1/skills/gap-analysis returns 200 OK with valid schema."""
    async def _impl():
        user_id = uuid.uuid4()
        mock_user = User(id=user_id, email="cand@test.com")
        mock_db = _make_mock_db()
        saved = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/skills/gap-analysis?target_role=staff_principal")
                assert resp.status_code == 200
                data = resp.json()
                assert data["target_role"] == "staff_principal"
                assert "overall_readiness_pct" in data and len(data["categories"]) == 6
                assert "recommendations" in data and "strengths" in data and "critical_gaps" in data
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved)

    asyncio.run(_impl())


def test_api_get_skill_gap_analysis_unauthenticated():
    """Verify unauthenticated request returns 401 Unauthorized."""
    async def _impl():
        saved = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/skills/gap-analysis")
                assert resp.status_code == 401
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved)

    asyncio.run(_impl())
