"""Hermetic unit and API integration tests for Step 5.1a Public Defense Reports & Badges."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import defense_store
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.defense import DefenseSessionState, DefenseStage
from app.schemas.report import CategoryScore, EnhancedDefenseReportResponse
from app.services.public_report import (
    PublicReportStore,
    PublicShareRecord,
    determine_certification_tier,
    generate_defense_svg_badge,
    public_share_store,
    resolve_public_report,
)


@pytest.fixture(autouse=True)
def cleanup_stores():
    """Ensures in-memory stores are captured and restored."""
    saved_tokens = dict(public_share_store._tokens)
    saved_sessions = dict(public_share_store._session_tokens)
    saved_defense = dict(defense_store._sessions)
    public_share_store._tokens.clear()
    public_share_store._session_tokens.clear()
    defense_store._sessions.clear()
    try:
        yield
    finally:
        public_share_store._tokens = saved_tokens
        public_share_store._session_tokens = saved_sessions
        defense_store._sessions = saved_defense


def _make_mock_db(project: Project = None, snapshot: RepositorySnapshot = None) -> AsyncMock:
    """Build mock AsyncSession returning configured Project and RepositorySnapshot."""
    mock_db = AsyncMock()

    async def _exec(stmt):
        res = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repository_snapshots" in stmt_str or "repository_snapshot" in stmt_str:
            res.scalar_one_or_none.return_value = snapshot
        elif "from projects" in stmt_str:
            res.scalar_one_or_none.return_value = project
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute = AsyncMock(side_effect=_exec)
    return mock_db


def test_determine_certification_tier():
    """Verifies classification into standard certification tiers."""
    assert determine_certification_tier(8.5, "Strong defense") == "Certified Principal"
    assert determine_certification_tier(7.0, "Certified Principal Defense") == "Certified Principal"
    assert determine_certification_tier(6.5, "Solid Defense") == "Solid Architect"
    assert determine_certification_tier(5.0, "Passed") == "Solid Architect"
    assert determine_certification_tier(4.2, "Needs Work") == "Remediation Required"


def test_generate_defense_svg_badge():
    """Verifies dynamic SVG badge format, colors, and accessibility attributes."""
    svg_principal = generate_defense_svg_badge("Certified Principal", 8.8)
    assert "<svg" in svg_principal and "</svg>" in svg_principal
    assert "RepoDefense: Certified Principal • 8.8/10" in svg_principal
    assert "#059669" in svg_principal  # Emerald

    svg_solid = generate_defense_svg_badge("Solid Architect", 6.2)
    assert "#0284c7" in svg_solid  # Sky

    svg_remediation = generate_defense_svg_badge("Remediation Required", 3.5)
    assert "#d97706" in svg_remediation  # Amber


@pytest.mark.anyio
async def test_public_share_store_crud():
    """Verifies thread-safe in-memory CRUD operations on public_share_store."""
    now = datetime.now(timezone.utc)
    record = PublicShareRecord(
        share_token="rd_test123",
        session_id="sess_1",
        project_id="proj_1",
        user_id="user_1",
        is_active=True,
        created_at=now,
    )
    await public_share_store.save(record)
    assert (await public_share_store.get_by_token("rd_test123")).session_id == "sess_1"
    assert (await public_share_store.get_by_session("sess_1")).share_token == "rd_test123"
    assert await public_share_store.delete_by_session("sess_1") is True
    assert await public_share_store.get_by_token("rd_test123") is None

    # Capacity eviction does not evict existing token on update
    small = PublicReportStore(max_capacity=2)
    await small.save(PublicShareRecord("t1", "s1", "p1", "u1", True, now))
    await small.save(PublicShareRecord("t2", "s2", "p2", "u2", True, now))
    await small.save(PublicShareRecord("t1", "s1", "p1", "u1", False, now))
    assert (await small.get_by_token("t1")).is_active is False
    assert (await small.get_by_token("t2")) is not None


@pytest.mark.anyio
async def test_resolve_public_report_success():
    """Verifies compilation of public-safe verified defense report."""
    user_id, proj_id, session_id = uuid.uuid4(), uuid.uuid4(), str(uuid.uuid4())
    token, now = "rd_valid_token_xyz", datetime.now(timezone.utc)

    await public_share_store.save(
        PublicShareRecord(token, session_id, str(proj_id), str(user_id), True, now)
    )
    await defense_store.save(
        DefenseSessionState(
            session_id=session_id, project_id=str(proj_id),
            status=DefenseStage.SESSION_COMPLETED, current_question_index=1,
            questions=[], transcript=[],
            created_at=now.isoformat(), updated_at=now.isoformat(),
        )
    )
    project = Project(
        id=proj_id,
        user_id=user_id,
        name="test-repo",
        github_url="https://github.com/org/test-repo",
        status="analyzed",
    )
    snapshot = RepositorySnapshot(id=uuid.uuid4(), project_id=proj_id, commit_hash="abcdef123456")
    mock_db = _make_mock_db(project=project, snapshot=snapshot)

    mock_enhanced = EnhancedDefenseReportResponse(
        session_id=uuid.UUID(session_id),
        project_id=proj_id,
        overall_score=8.4,
        verdict="Certified Principal Defense",
        summary="Candidate showed exceptional command.",
        category_scores=[
            CategoryScore(
                category="architecture", score=8.5, questions_count=2,
                status="passed", summary="Solid patterns",
            )
        ],
        key_strengths=["Clean boundaries"], critical_blind_spots=[],
        actionable_recommendations=[], total_questions=2,
        completed_at=now.isoformat(), architecture_primary_pattern="Layered",
        tech_health_score=95,
    )

    with patch(
        "app.services.public_report.generate_enhanced_defense_report",
        return_value=mock_enhanced,
    ):
        report, _ = await resolve_public_report(token, mock_db)
        assert report.verification_id == token
        assert report.project_name == "test-repo"
        assert report.commit_hash == "abcdef1"
        assert report.overall_score == 8.4
        assert report.certification_tier == "Certified Principal"
        assert len(report.category_scores) == 1


@pytest.mark.anyio
async def test_resolve_public_report_expired_and_revoked():
    """Verifies that expired and revoked tokens are cleanly rejected."""
    token, past = "rd_expired_token", datetime.now(timezone.utc) - timedelta(days=2)
    record = PublicShareRecord(
        share_token=token,
        session_id="sess_exp",
        project_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        is_active=True,
        created_at=past,
        expires_at=past + timedelta(days=1),
    )
    await public_share_store.save(record)
    mock_db = _make_mock_db()

    with pytest.raises(ValueError, match="Public share link has expired"):
        await resolve_public_report(token, mock_db)

    record.is_active, record.expires_at = False, None
    await public_share_store.save(record)
    with pytest.raises(KeyError, match="revoked"):
        await resolve_public_report(token, mock_db)


@pytest.mark.anyio
async def test_api_public_reports_flow():
    """Comprehensive test for create, retrieve, public access, and revoke endpoints."""
    user_id, proj_id, session_id = uuid.uuid4(), uuid.uuid4(), str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    user = User(id=user_id, email="dev@example.com")
    project = Project(
        id=proj_id,
        user_id=user_id,
        name="secure-api",
        github_url="https://github.com/org/secure-api",
        status="analyzed",
    )
    snapshot = RepositorySnapshot(id=uuid.uuid4(), project_id=proj_id, commit_hash="deadbeef123456")
    session = DefenseSessionState(
        session_id=session_id,
        project_id=str(proj_id),
        status=DefenseStage.SESSION_COMPLETED,
        current_question_index=1,
        questions=[],
        transcript=[],
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )
    await defense_store.save(session)

    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: _make_mock_db(project=project, snapshot=snapshot)

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create Share Token (Authenticated with Referer)
            res = await client.post(
                f"/api/v1/projects/{proj_id}/defense/{session_id}/share",
                headers={"referer": "https://dashboard.example.com/p/1?k=v#frag"},
                json={"is_active": True, "expires_in_days": 30},
            )
            assert res.status_code == 200
            token = res.json()["share_token"]
            assert token.startswith("rd_")
            assert res.json()["share_url"].startswith("https://dashboard.example.com/verify/")

            # 2. Get Share Info (Authenticated)
            info = await client.get(
                f"/api/v1/projects/{proj_id}/defense/{session_id}/share",
                headers={"referer": "https://dashboard.example.com/other"},
            )
            assert info.status_code == 200
            assert info.json()["share_token"] == token
            assert info.json()["share_url"].startswith("https://dashboard.example.com/verify/")

            # 3. Public Report & SVG Badge (Unauthenticated)
            mock_rep = EnhancedDefenseReportResponse(
                session_id=uuid.UUID(session_id),
                project_id=proj_id,
                overall_score=7.8,
                verdict="Certified Principal Defense",
                summary="Great defense.",
                category_scores=[], key_strengths=["Architecture"],
                critical_blind_spots=[], actionable_recommendations=[],
                total_questions=1, completed_at=now.isoformat(),
            )
            with patch(
                "app.services.public_report.generate_enhanced_defense_report",
                return_value=mock_rep,
            ):
                pub = await client.get(f"/api/v1/public/reports/{token}")
                assert pub.status_code == 200
                assert pub.json()["project_name"] == "secure-api"

                badge = await client.get(f"/api/v1/public/badges/{token}.svg")
                assert badge.status_code == 200
                assert "image/svg+xml" in badge.headers["content-type"]
                assert "Certified Principal" in badge.text

            # 4. IDOR verification: User B cannot delete User A's share
            attacker = User(id=uuid.uuid4(), email="attacker@example.com")
            attacker_proj = Project(
                id=uuid.uuid4(),
                user_id=attacker.id,
                name="attacker-repo",
                github_url="https://github.com/attacker/repo",
            )
            app.dependency_overrides[get_current_user] = lambda: attacker
            app.dependency_overrides[get_db] = lambda: _make_mock_db(project=attacker_proj)

            idor_res = await client.delete(
                f"/api/v1/projects/{attacker_proj.id}/defense/{session_id}/share"
            )
            assert idor_res.status_code == 404

            # 5. Legitimate owner revokes & verify 404
            app.dependency_overrides[get_current_user] = lambda: user
            app.dependency_overrides[get_db] = lambda: _make_mock_db(project=project)
            rev = await client.delete(f"/api/v1/projects/{proj_id}/defense/{session_id}/share")
            assert rev.status_code == 200 and rev.json()["revoked"] is True
            assert (await client.get(f"/api/v1/public/reports/{token}")).status_code == 404
    finally:
        app.dependency_overrides = saved_overrides
