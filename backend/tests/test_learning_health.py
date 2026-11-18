"""
Hermetic unit and integration tests for Step 4.7a Learning Loop Telemetry & Health Probe.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import get_read_only_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
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


def _make_mock_db(
    skill_count: int = 10,
    weak_count: int = 3,
    should_fail: bool = False,
    weak_fails: bool = False,
) -> AsyncMock:
    """Build mock AsyncSession returning count scalars or raising exception."""
    mock_db = AsyncMock()
    if should_fail:
        mock_db.execute.side_effect = RuntimeError("Database connection pool timeout")
        return mock_db

    async def _exec(stmt):
        if weak_fails and "candidate_weaknesses" in str(stmt):
            raise RuntimeError("Candidate weaknesses query failed")
        res = MagicMock()
        res.scalar.return_value = (
            weak_count if "candidate_weaknesses" in str(stmt) else skill_count
        )
        return res

    mock_db.execute.side_effect = _exec
    return mock_db


def test_schema_validations():
    """Verify schema constraints, required fields, and forbidding extra fields."""
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

    with pytest.raises(ValidationError):
        DatabaseModelsHealth(
            status=ComponentHealthStatus.HEALTHY,
            user_skills_accessible=True,
            candidate_weaknesses_accessible=True,
            unrecognized_field="forbidden",
        )


def test_inspect_benchmark_profiles_health():
    """Verify benchmark catalog audit passes with valid configurations."""
    health = inspect_benchmark_profiles_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.tier_integrity_verified is True
    assert len(health.configured_tiers) == 3
    assert health.total_categories == 6
    assert health.detail is None


def test_inspect_benchmark_profiles_degraded():
    """Verify degraded status when required tiers are missing."""
    with patch("app.services.learning_health.BENCHMARK_PROFILES", {}):
        health = inspect_benchmark_profiles_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert health.tier_integrity_verified is False
        assert "Missing required benchmark tiers" in str(health.detail)


def test_inspect_benchmark_profiles_invalid_domains_and_types():
    """Verify degraded status on missing domains or non-numeric target/weight."""
    bad_domains = {
        TargetRoleBenchmark.MID_LEVEL: {
            "system_architecture": {"target": 65.0, "weight": 1.2}
        },
        TargetRoleBenchmark.SENIOR_ENGINEER: {},
        TargetRoleBenchmark.STAFF_PRINCIPAL: {},
    }
    with patch("app.services.learning_health.BENCHMARK_PROFILES", bad_domains):
        health = inspect_benchmark_profiles_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert "Missing required domains" in str(health.detail)

    bad_types = {
        TargetRoleBenchmark.MID_LEVEL: {
            dom: {"target": "invalid_str", "weight": 1.0}
            for dom in [
                "system_architecture",
                "database_design",
                "concurrency_performance",
                "security_isolation",
                "reliability_observability",
                "api_contract_design",
            ]
        },
        TargetRoleBenchmark.SENIOR_ENGINEER: {},
        TargetRoleBenchmark.STAFF_PRINCIPAL: {},
    }
    with patch("app.services.learning_health.BENCHMARK_PROFILES", bad_types):
        health = inspect_benchmark_profiles_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert "Invalid target/weight" in str(health.detail)


def test_inspect_mentor_service_health():
    """Verify mentor fallback synthesis inspection returns healthy."""
    health = inspect_mentor_service_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.fallbacks_ready is True
    assert "connection_pooling" in health.supported_fallback_topics


def test_inspect_mentor_service_failure():
    """Verify degraded status when fallback generator raises exception."""
    with patch(
        "app.services.learning_health.build_deterministic_mentor_explanation",
        side_effect=RuntimeError("Template formatting error"),
    ):
        health = inspect_mentor_service_health()
        assert health.status == ComponentHealthStatus.DEGRADED
        assert health.fallbacks_ready is False
        assert health.detail == "Fallback synthesis error"


def test_inspect_retest_service_health():
    """Verify retest bounded cache status inspection returns healthy."""
    health = inspect_retest_service_health()
    assert health.status == ComponentHealthStatus.HEALTHY
    assert health.cache_active is True
    assert health.max_cache_capacity == 1000
    assert health.cached_question_count >= 0


@pytest.mark.anyio
async def test_inspect_database_models_health_success():
    """Verify database model inspection returns healthy when queries succeed."""
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
    """Verify database model inspection returns degraded on partial query failure."""
    mock_db = _make_mock_db(skill_count=12, weak_count=0, weak_fails=True)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.DEGRADED
    assert health.user_skills_accessible is True
    assert health.candidate_weaknesses_accessible is False
    assert health.total_user_skills == 12
    assert health.total_candidate_weaknesses == 0
    assert "CandidateWeakness table inaccessible" in str(health.detail)


@pytest.mark.anyio
async def test_inspect_database_models_health_failure():
    """Verify database model inspection returns unhealthy when query fails."""
    mock_db = _make_mock_db(should_fail=True)
    health = await inspect_database_models_health(mock_db)
    assert health.status == ComponentHealthStatus.UNHEALTHY
    assert health.user_skills_accessible is False
    assert health.candidate_weaknesses_accessible is False
    assert health.detail == "Database query failed"


@pytest.mark.anyio
async def test_inspect_learning_loop_overall_healthy():
    """Verify aggregated response returns healthy when all subsystems pass."""
    mock_db = _make_mock_db(skill_count=15, weak_count=3)
    res = await inspect_learning_loop_health(mock_db)
    assert isinstance(res, LearningLoopHealthResponse)
    assert res.status == ComponentHealthStatus.HEALTHY
    assert res.database_models.status == ComponentHealthStatus.HEALTHY
    assert res.benchmark_profiles.status == ComponentHealthStatus.HEALTHY
    assert res.mentor_service.status == ComponentHealthStatus.HEALTHY
    assert res.retest_service.status == ComponentHealthStatus.HEALTHY


@pytest.mark.anyio
async def test_inspect_learning_loop_overall_unhealthy():
    """Verify aggregated response returns unhealthy when database fails."""
    mock_db = _make_mock_db(should_fail=True)
    res = await inspect_learning_loop_health(mock_db)
    assert res.status == ComponentHealthStatus.UNHEALTHY
    assert res.database_models.status == ComponentHealthStatus.UNHEALTHY


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_200():
    """Verify GET /api/v1/health/learning-loop returns 200 OK when authenticated."""
    mock_db = _make_mock_db(skill_count=20, weak_count=5)
    mock_user = User(id=str(uuid.uuid4()), email="admin@repodefense.com")
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_read_only_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["database_models"]["total_user_skills"] == 20
            assert data["benchmark_profiles"]["tier_integrity_verified"] is True
            assert data["mentor_service"]["fallbacks_ready"] is True
            assert data["retest_service"]["cache_active"] is True
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_503():
    """Verify GET /api/v1/health/learning-loop returns 503 when database is unhealthy."""
    mock_db = _make_mock_db(should_fail=True)
    mock_user = User(id=str(uuid.uuid4()), email="admin@repodefense.com")
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_read_only_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["database_models"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.mark.anyio
async def test_api_get_learning_loop_health_endpoint_401():
    """Verify GET /api/v1/health/learning-loop returns 401 when unauthenticated."""
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/learning-loop")
            assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
