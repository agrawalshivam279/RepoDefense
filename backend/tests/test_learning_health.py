"""
Hermetic unit and integration tests for Step 4.7a Learning Loop Telemetry & Health Probe.
"""

import copy
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import get_read_only_db
from app.core.security import get_current_token_payload
from app.main import app
from app.schemas.auth import TokenPayload
from app.schemas.learning_health import (
    ComponentHealthStatus,
    DatabaseModelsHealth,
    LearningLoopHealthResponse,
)
from app.schemas.skill_gap import TargetRoleBenchmark
from app.services.learning_health import (
    inspect_benchmark_profiles_health,
    inspect_database_models_health,
    inspect_learning_loop_health,
    inspect_mentor_service_health,
    inspect_retest_service_health,
)
from app.services.skill_gap import BENCHMARK_PROFILES


def _make_mock_db(
    skill_count: int = 10,
    weak_count: int = 3,
    should_fail: bool = False,
    skill_fails: bool = False,
    weak_fails: bool = False,
) -> AsyncMock:
    mock_db = AsyncMock()
    if should_fail:
        mock_db.execute.side_effect = RuntimeError("Database connection pool timeout")
        return mock_db

    async def _exec(stmt):
        stmt_str = str(stmt).lower()
        if "user_skills" in stmt_str:
            if skill_fails:
                raise RuntimeError("User skills query failed")
            res = MagicMock()
            res.scalar.return_value = skill_count
            return res
        if "candidate_weaknesses" in stmt_str:
            if weak_fails:
                raise RuntimeError("Candidate weaknesses query failed")
            res = MagicMock()
            res.scalar.return_value = weak_count
            return res
        raise ValueError(f"Unexpected query statement: {stmt}")

    mock_db.execute.side_effect = _exec
    return mock_db


def test_schema_validations():
    db_health = DatabaseModelsHealth(
        status=ComponentHealthStatus.HEALTHY,
        user_skills_accessible=True,
        candidate_weaknesses_accessible=True,
        total_user_skills=5,
        total_candidate_weaknesses=2,
    )
    assert db_health.status == ComponentHealthStatus.HEALTHY
    assert db_health.total_user_skills == 5

    with pytest.raises(ValidationError):
        DatabaseModelsHealth(
            status=ComponentHealthStatus.HEALTHY,
            user_skills_accessible=True,
            candidate_weaknesses_accessible=True,
            total_user_skills=-1,
        )


def test_inspect_benchmark_profiles_health():
    health = inspect_benchmark_profiles_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.tier_integrity_verified is True
    assert len(health.configured_tiers) == 3
    assert health.total_categories == 6
    assert health.detail is None


@pytest.mark.parametrize(
    "bad_meta",
    [
        {"target": False, "weight": 1.0},
        {"target": 10**400, "weight": 1.0},
        {"target": 50.0, "weight": True},
        {"target": 50.0, "weight": 10**400},
        {"target": 50.0, "weight": 6.0},
        {"target": float("nan"), "weight": 1.0},
        {"target": float("inf"), "weight": 1.0},
        {"target": "invalid_str", "weight": 1.0},
    ],
)
def test_inspect_benchmark_profiles_edge_cases(bad_meta):
    bad = copy.deepcopy(BENCHMARK_PROFILES)
    bad[TargetRoleBenchmark.MID_LEVEL]["system_architecture"] = bad_meta
    with patch("app.services.learning_health.BENCHMARK_PROFILES", bad):
        health = inspect_benchmark_profiles_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert "Invalid target/weight in tier 'mid_level' for domain 'system_architecture'" in str(
            health.detail
        )


def test_inspect_benchmark_profiles_unsupported_tier_key():
    with patch(
        "app.services.learning_health.BENCHMARK_PROFILES", {"experimental": {}}
    ):
        health = inspect_benchmark_profiles_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert "experimental" in health.configured_tiers


def test_inspect_mentor_service_health():
    health = inspect_mentor_service_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.fallbacks_ready is True
    assert "connection_pooling" in health.supported_fallback_topics


def test_inspect_mentor_service_failure():
    with patch(
        "app.services.learning_health.build_deterministic_mentor_explanation",
        side_effect=RuntimeError("Template formatting error"),
    ):
        health = inspect_mentor_service_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert health.fallbacks_ready is False
        assert health.detail == "Fallback synthesis error"


def test_inspect_retest_service_health():
    health = inspect_retest_service_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.cache_active is True
    assert health.max_cache_capacity == 1000
    assert health.cached_question_count >= 0


def test_inspect_retest_service_over_capacity():
    with patch(
        "app.services.learning_health._ACTIVE_RETEST_QUESTIONS", ["q"] * 1001
    ):
        health = inspect_retest_service_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert "exceed capacity" in str(health.detail)


@pytest.mark.anyio
async def test_inspect_database_models_health_success():
    mock_db = _make_mock_db(skill_count=12, weak_count=4)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.user_skills_accessible is True
    assert health.candidate_weaknesses_accessible is True
    assert health.total_user_skills == 12
    assert health.total_candidate_weaknesses == 4
    assert health.detail is None


@pytest.mark.anyio
async def test_inspect_database_models_health_partial_failure():
    mock_db = _make_mock_db(skill_count=12, weak_count=0, weak_fails=True)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.DEGRADED
    assert health.user_skills_accessible is True
    assert health.candidate_weaknesses_accessible is False
    assert health.total_user_skills == 12
    assert health.total_candidate_weaknesses == 0
    assert "CandidateWeakness table inaccessible" in str(health.detail)


@pytest.mark.anyio
async def test_inspect_database_models_first_query_failure_rolls_back():
    mock_db = _make_mock_db(skill_count=0, weak_count=8, skill_fails=True)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.DEGRADED
    assert health.user_skills_accessible is False
    assert health.candidate_weaknesses_accessible is True
    assert health.total_candidate_weaknesses == 8
    mock_db.rollback.assert_called_once()


@pytest.mark.anyio
async def test_inspect_database_models_health_failure():
    mock_db = _make_mock_db(should_fail=True)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.UNHEALTHY
    assert health.user_skills_accessible is False
    assert health.candidate_weaknesses_accessible is False
    assert health.detail == "Database query failed"


@pytest.mark.anyio
async def test_inspect_learning_loop_overall_healthy():
    mock_db = _make_mock_db(skill_count=15, weak_count=3)
    res = await inspect_learning_loop_health(mock_db)
    assert isinstance(res, LearningLoopHealthResponse)
    assert res.status == ComponentHealthStatus.HEALTHY
    assert res.database_models.status == ComponentHealthStatus.HEALTHY


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_200():
    mock_db = _make_mock_db(skill_count=20, weak_count=5)
    token = TokenPayload(
        sub=uuid.uuid4(),
        email="admin@repodefense.com",
        exp=9999999999,
        aud="authenticated",
        role="authenticated",
    )
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_read_only_db] = lambda: mock_db
    app.dependency_overrides[get_current_token_payload] = lambda: token
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["database_models"]["total_user_skills"] == 20
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_503():
    mock_db = _make_mock_db(should_fail=True)
    token = TokenPayload(
        sub=uuid.uuid4(),
        email="admin@repodefense.com",
        exp=9999999999,
        aud="authenticated",
        role="authenticated",
    )
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_read_only_db] = lambda: mock_db
    app.dependency_overrides[get_current_token_payload] = lambda: token
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_401():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_token_payload, None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
