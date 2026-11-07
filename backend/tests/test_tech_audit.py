"""Hermetic unit and integration tests for technology health audit engine."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.analyzers.tech_audit import (
    audit_dependencies_list,
    audit_dependency,
    calculate_tech_health_score,
    parse_semver,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.schemas.tech_audit import AuditCategory, AuditSeverity
from app.services.tech_audit import audit_project_technology
from tests.test_auth import create_test_jwt


def test_parse_semver_variations():
    """Verify semantic version parsing across operators and suffixes."""
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("^16.8.0") == (16, 8, 0)
    assert parse_semver("~2.0.7") == (2, 0, 7)
    assert parse_semver(">=3.10.1") == (3, 10, 1)
    assert parse_semver("v4.17.21") == (4, 17, 21)
    assert parse_semver("4.17.21-beta.1") == (4, 17, 21)
    assert parse_semver("invalid") is None
    assert parse_semver("") is None
    assert parse_semver(None) is None


def test_audit_dependency_static_deprecated_rules():
    """Verify static package deprecation identification."""
    req_item = audit_dependency("request", None)
    assert req_item is not None
    assert req_item.severity == AuditSeverity.HIGH
    assert req_item.category == AuditCategory.DEPRECATED
    assert "deprecated" in req_item.issue_description.lower()

    moment_item = audit_dependency("moment", "2.29.4")
    assert moment_item is not None
    assert moment_item.severity == AuditSeverity.LOW
    assert moment_item.category == AuditCategory.UNMAINTAINED

    clean_item = audit_dependency("safe-pkg", "1.0.0")
    assert clean_item is None


def test_audit_dependency_version_thresholds():
    """Verify version-based vulnerability and obsolescence thresholds."""
    # Lodash prototype pollution (< 4.17.21)
    item_vulnerable = audit_dependency("lodash", "4.17.15")
    assert item_vulnerable is not None
    assert item_vulnerable.severity == AuditSeverity.CRITICAL
    assert item_vulnerable.category == AuditCategory.SECURITY_RISK

    item_safe = audit_dependency("lodash", "4.17.21")
    assert item_safe is None

    # urllib3 request body injection (< 2.0.7)
    item_urllib = audit_dependency("urllib3", "^1.26.5")
    assert item_urllib is not None
    assert item_urllib.severity == AuditSeverity.HIGH
    assert item_urllib.category == AuditCategory.SECURITY_RISK

    # react < 18.0.0
    item_react = audit_dependency("react", "17.0.2")
    assert item_react is not None
    assert item_react.severity == AuditSeverity.MEDIUM
    assert item_react.category == AuditCategory.OUTDATED


def test_calculate_tech_health_score_clamping():
    """Verify health score deduction arithmetic and 0-100 clamping."""
    assert calculate_tech_health_score(0, 0, 0, 0, 0) == 100
    assert calculate_tech_health_score(0, 0, 0, 0, 10) == 100

    # 1 critical (-25) -> 75
    assert calculate_tech_health_score(1, 0, 0, 0, 5) == 75

    # 1 critical (-25) + 2 high (-30) + 1 medium (-8) + 1 low (-3) -> 100 - 66 = 34
    assert calculate_tech_health_score(1, 2, 1, 1, 10) == 34

    # Heavy deductions clamp at 0
    assert calculate_tech_health_score(5, 5, 5, 5, 20) == 0


def test_audit_dependencies_list_aggregation():
    """Verify batch dependency auditing returns correct counts and items."""
    deps = [
        ("request", "2.88.2", False),
        ("lodash", "4.17.15", False),
        ("fastapi", "0.110.0", False),
        ("pytest", "8.0.0", True),
    ]
    items, score, counts = audit_dependencies_list(deps)
    assert len(items) == 2
    assert counts["critical"] == 1
    assert counts["high"] == 1
    assert score == 60  # 100 - 25 - 15 = 60


def _build_test_db(project_id: uuid.UUID, user_id: uuid.UUID, deps: list):
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    user = User(
        id=user_id,
        email="test@repodefense.com",
        created_at=now,
        updated_at=now,
    )
    project = Project(
        id=project_id,
        user_id=user_id,
        name="AuditRepo",
        github_url="https://github.com/test/audit",
        default_branch="main",
        status="completed",
        created_at=now,
        updated_at=now,
    )

    def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "from projects" in stmt_str:
            res.scalar_one_or_none.return_value = project
        elif "from dependencies" in stmt_str:
            res.all.return_value = deps
        else:
            res.scalar_one_or_none.return_value = None
            res.all.return_value = []
        return res

    mock_db.execute.side_effect = mock_execute
    return mock_db, project, user


@pytest.mark.anyio
async def test_audit_project_technology_service():
    """Verify technology audit service retrieves DB records and generates report."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, project, _ = _build_test_db(
        project_id=p_id,
        user_id=u_id,
        deps=[
            ("request", "2.88.2", False),
            ("fastapi", "0.110.0", False),
        ],
    )

    report = await audit_project_technology(project, mock_db)
    assert report.project_id == str(p_id)
    assert report.total_dependencies_audited == 2
    assert report.flagged_dependencies_count == 1
    assert report.high_count == 1
    assert report.tech_health_score == 85
    assert len(report.audited_items) == 1
    assert report.audited_items[0].name == "request"


@pytest.mark.anyio
async def test_tech_audit_endpoint_success():
    """Verify GET /api/v1/projects/{project_id}/tech-audit returns 200 OK."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, _, user = _build_test_db(
        project_id=p_id,
        user_id=u_id,
        deps=[("lodash", "4.17.15", False)],
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        token = create_test_jwt(str(u_id), "audit@example.com")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/projects/{p_id}/tech-audit",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == str(p_id)
            assert data["total_dependencies_audited"] == 1
            assert data["critical_count"] == 1
            assert data["tech_health_score"] == 75
            assert len(data["audited_items"]) == 1
            assert data["audited_items"][0]["name"] == "lodash"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_tech_audit_endpoint_not_found():
    """Verify GET /api/v1/projects/{project_id}/tech-audit returns 404 for missing project."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res
    user = User(id=u_id, email="missing@example.com")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        token = create_test_jwt(str(u_id), "missing@example.com")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/projects/{p_id}/tech-audit",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_tech_audit_endpoint_forbidden():
    """Verify GET /api/v1/projects/{project_id}/tech-audit returns 403 on non-owner."""
    p_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    mock_db, _, _ = _build_test_db(
        project_id=p_id,
        user_id=owner_id,
        deps=[],
    )
    other_user = User(id=other_user_id, email="intruder@example.com")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: other_user

    try:
        transport = ASGITransport(app=app)
        token = create_test_jwt(str(other_user_id), "intruder@example.com")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/projects/{p_id}/tech-audit",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
