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
            current_score=105.0,  # invalid > 100
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
            rationale="1234",  # < 5 chars
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
        assert "system_architecture" in profile
        assert "database_design" in profile
        assert "concurrency_performance" in profile
        for cat, meta in profile.items():
            assert 0.0 < meta["target"] <= 100.0
            assert 0.0 < meta["weight"] <= 5.0


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
        assert resp.overall_candidate_score == 0.0
        assert resp.overall_readiness_pct == 0.0
        assert len(resp.categories) == 6
        for c in resp.categories:
            assert c.current_score == 0.0
            assert c.status == GapStatus.CRITICAL_GAP
        assert len(resp.strengths) == 0
        assert len(resp.critical_gaps) == 6
        assert len(resp.recommendations) > 0

    asyncio.run(_impl())


def test_analyze_skill_gaps_populated_skills():
    """Verify gap calculations, percentile estimates, and weakness-driven recommendations."""
    async def _impl():
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        skills = [
            UserSkill(
                id=uuid.uuid4(),
                user_id=user_id,
                category="system_architecture",
                topic="microservices",
                proficiency_score=92.0,
                total_evaluations=3,
                passed_evaluations=3,
                failed_evaluations=0,
                last_evaluated_at=now,
            ),
            UserSkill(
                id=uuid.uuid4(),
                user_id=user_id,
                category="database_design",
                topic="indexing",
                proficiency_score=80.0,
                total_evaluations=2,
                passed_evaluations=2,
                failed_evaluations=0,
                last_evaluated_at=now,
            ),
            UserSkill(
                id=uuid.uuid4(),
                user_id=user_id,
                category="concurrency_performance",
                topic="race_conditions",
                proficiency_score=60.0,
                total_evaluations=1,
                passed_evaluations=0,
                failed_evaluations=1,
                last_evaluated_at=now,
            ),
        ]

        weaknesses = [
            CandidateWeakness(
                id=uuid.uuid4(),
                user_id=user_id,
                project_id=uuid.uuid4(),
                simulation_mode="defense",
                category="concurrency_performance",
                topic="race_conditions",
                severity="critical",
                question_prompt="Address race conditions in middleware",
                feedback="Candidate missed locking primitives",
                resolved=False,
            ),
        ]

        mock_db = _make_mock_db(skills=skills, weaknesses=weaknesses)

        resp = await skill_gap_service.analyze_skill_gaps(
            db=mock_db,
            user_id=user_id,
            target_role=TargetRoleBenchmark.SENIOR_ENGINEER,
        )

        assert resp.overall_candidate_score > 0.0
        assert resp.overall_readiness_pct > 0.0

        sys_arch = next(c for c in resp.categories if c.category == "system_architecture")
        assert sys_arch.current_score == 92.0
        assert sys_arch.benchmark_score == 85.0
        assert sys_arch.status == GapStatus.SURPASSED
        assert "system_architecture" in resp.strengths

        db_design = next(c for c in resp.categories if c.category == "database_design")
        assert db_design.current_score == 80.0
        assert db_design.status == GapStatus.MET

        concur = next(c for c in resp.categories if c.category == "concurrency_performance")
        assert concur.current_score == 60.0
        assert concur.gap_deficit == 20.0
        assert concur.status == GapStatus.MODERATE_GAP

        # Priority recommendation from active weakness
        assert len(resp.recommendations) > 0
        top_rec = resp.recommendations[0]
        assert top_rec.priority == RemediationPriority.CRITICAL
        assert top_rec.unresolved_weakness_count == 1
        assert "Race Conditions" in top_rec.topic

    asyncio.run(_impl())


def test_api_get_skill_gap_analysis_authenticated():
    """Verify GET /api/v1/skills/gap-analysis returns 200 OK with valid schema."""
    async def _impl():
        user_id = uuid.uuid4()
        mock_user = User(id=user_id, email="cand@test.com")
        mock_db = _make_mock_db()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/skills/gap-analysis?target_role=staff_principal")
                assert resp.status_code == 200
                data = resp.json()
                assert data["target_role"] == "staff_principal"
                assert "overall_readiness_pct" in data
                assert len(data["categories"]) == 6
                assert "recommendations" in data
                assert "strengths" in data
                assert "critical_gaps" in data
        finally:
            app.dependency_overrides.clear()

    asyncio.run(_impl())


def test_api_get_skill_gap_analysis_unauthenticated():
    """Verify unauthenticated request returns 401 Unauthorized."""
    async def _impl():
        app.dependency_overrides.clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/skills/gap-analysis")
            assert resp.status_code == 401

    asyncio.run(_impl())
