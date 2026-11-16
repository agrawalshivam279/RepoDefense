"""Unit and API contract tests for Step 4.1b Weakness Tracker Service & REST API."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.skill import RecordEvaluationRequest, WeaknessSeverity
from app.services.weakness_tracker import (
    get_candidate_weaknesses,
    get_user_skills_overview,
    record_evaluation_turn,
    resolve_weakness,
)


def _make_mock_db(scalar_return=None, scalars_return=None):
    """Build mock AsyncSession returning specified scalar/scalars."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.add_all = MagicMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = scalar_return
    exec_res.scalar.return_value = scalar_return
    exec_res.scalars.return_value.all.return_value = (
        scalars_return if scalars_return is not None else []
    )
    mock_db.execute.return_value = exec_res
    return mock_db


def test_record_evaluation_turn_creates_user_skill_and_weakness():
    """Verify first failed evaluation creates skill and extracts 384-dim weakness."""
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        mock_db = _make_mock_db(scalar_return=None)

        skill, weakness = await record_evaluation_turn(
            session=mock_db,
            user_id=uid,
            project_id=pid,
            simulation_mode="core_defense",
            category="scalability",
            topic="connection_pooling",
            question_prompt="What happens if pool is exhausted?",
            feedback="Requests will queue and timeout.",
            passed=False,
            score=30.0,
        )

        assert skill is not None and weakness is not None
        assert skill.user_id == uid and skill.category == "scalability"
        assert skill.topic == "connection_pooling" and skill.proficiency_score == 30.0
        assert skill.total_evaluations == 1 and skill.failed_evaluations == 1
        assert weakness.user_id == uid and weakness.severity == WeaknessSeverity.CRITICAL.value
        assert weakness.resolved is False and len(weakness.topic_embedding) == 384
        assert mock_db.flush.called

    asyncio.run(_impl())


def test_record_evaluation_turn_updates_existing_skill_moving_average():
    """Verify moving average formula on subsequent evaluation without weakness."""
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        now = datetime.now(timezone.utc)
        existing_skill = UserSkill(
            id=uuid.uuid4(), user_id=uid, category="reliability", topic="circuit_breaker",
            proficiency_score=50.0, total_evaluations=1, passed_evaluations=1,
            failed_evaluations=0, created_at=now, updated_at=now,
        )
        mock_db = _make_mock_db(scalar_return=existing_skill)

        # 50.0 * 0.7 + 90.0 * 0.3 = 35.0 + 27.0 = 62.0
        skill, weakness = await record_evaluation_turn(
            session=mock_db, user_id=uid, project_id=pid, simulation_mode="stress_test",
            category="reliability", topic="circuit_breaker",
            question_prompt="How do you handle downstream failure?",
            feedback="Graceful fallback implemented.", passed=True, score=90.0,
        )

        assert skill.proficiency_score == 62.0 and skill.total_evaluations == 2
        assert skill.passed_evaluations == 2 and weakness is None

    asyncio.run(_impl())


def test_resolve_weakness_success_and_skill_reinforcement():
    """Verify marking weakness resolved appends note and boosts skill proficiency."""
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        wid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        weakness = CandidateWeakness(
            id=wid, user_id=uid, project_id=pid, simulation_mode="incident_simulation",
            category="architecture", topic="event_bus", severity="major",
            question_prompt="Event ordering risk",
            feedback="Out of order processing causes split-brain.",
            resolved=False, created_at=now, updated_at=now,
        )
        associated_skill = UserSkill(
            user_id=uid, category="architecture", topic="event_bus",
            proficiency_score=60.0, total_evaluations=2, passed_evaluations=1,
            failed_evaluations=1, created_at=now, updated_at=now,
        )

        mock_db = AsyncMock()
        e1, e2 = MagicMock(), MagicMock()
        e1.scalar_one_or_none.return_value = weakness
        e2.scalar_one_or_none.return_value = associated_skill
        mock_db.execute = AsyncMock(side_effect=[e1, e2])

        resolved = await resolve_weakness(
            session=mock_db, weakness_id=wid, user_id=uid,
            feedback="Partition keys guarantee per-entity order.",
        )

        assert resolved is not None and resolved.resolved is True
        assert resolved.resolved_at is not None
        assert "[Resolution Note]: Partition keys guarantee" in resolved.feedback
        assert associated_skill.proficiency_score == 70.0
        assert associated_skill.passed_evaluations == 2

    asyncio.run(_impl())


def test_resolve_and_get_candidate_weaknesses_filters():
    """Verify unauthorized resolve returns None and get_candidate_weaknesses applies filters."""
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        mock_db = _make_mock_db(scalar_return=None, scalars_return=[])
        res = await resolve_weakness(mock_db, uuid.uuid4(), uuid.uuid4())
        assert res is None

        items = await get_candidate_weaknesses(
            mock_db, user_id=uid, project_id=pid, resolved=False, category="sec", limit=25
        )
        assert items == []

    asyncio.run(_impl())


def test_get_user_skills_overview_aggregation_and_ordering():
    """Verify KPI aggregation and severity ordering (critical first)."""
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        now = datetime.now(timezone.utc)
        skills = [
            UserSkill(
                id=uuid.uuid4(), user_id=uid, category="sec", topic="jwt",
                proficiency_score=80.0, total_evaluations=2, passed_evaluations=2,
                failed_evaluations=0, created_at=now, updated_at=now,
            ),
            UserSkill(
                id=uuid.uuid4(), user_id=uid, category="scale", topic="index",
                proficiency_score=50.0, total_evaluations=2, passed_evaluations=1,
                failed_evaluations=1, created_at=now, updated_at=now,
            ),
        ]
        unresolved = [
            CandidateWeakness(
                id=uuid.uuid4(), user_id=uid, project_id=pid, simulation_mode="core",
                category="scale", topic="index", severity="minor", question_prompt="q",
                feedback="f", resolved=False, created_at=now, updated_at=now,
            ),
            CandidateWeakness(
                id=uuid.uuid4(), user_id=uid, project_id=pid, simulation_mode="core",
                category="sec", topic="jwt", severity="critical", question_prompt="q",
                feedback="f", resolved=False, created_at=now, updated_at=now,
            ),
        ]

        mock_db = AsyncMock()
        e1, e2, e3 = MagicMock(), MagicMock(), MagicMock()
        e1.scalars.return_value.all.return_value = skills
        e2.scalars.return_value.all.return_value = unresolved
        e3.scalar.return_value = 1
        mock_db.execute = AsyncMock(side_effect=[e1, e2, e3])

        overview = await get_user_skills_overview(mock_db, uid)
        assert overview.total_skills_tracked == 2 and overview.avg_proficiency_pct == 65.0
        assert overview.weak_skills_count == 1 and overview.strong_skills_count == 1
        assert overview.unresolved_weaknesses_count == 2 and overview.resolved_weaknesses_count == 1
        assert overview.top_weaknesses[0].severity == WeaknessSeverity.CRITICAL

    asyncio.run(_impl())


def test_skills_rest_endpoints_auth_and_crud():
    """Verify API router authentication, overview, listing, and resolution."""
    async def _impl():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as anon:
            unauth = await anon.get("/api/v1/skills/overview")
            assert unauth.status_code in (401, 403)

        uid, pid = uuid.uuid4(), uuid.uuid4()
        now = datetime.now(timezone.utc)
        user = User(id=uid, email="candidate@repodefense.dev")
        mock_db = _make_mock_db()

        prev_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Overview endpoint
                with patch("app.api.v1.skills.get_user_skills_overview") as mock_ov:
                    mock_ov.return_value = {
                        "user_id": uid, "total_skills_tracked": 1, "avg_proficiency_pct": 75.0,
                        "weak_skills_count": 0, "strong_skills_count": 1,
                        "unresolved_weaknesses_count": 0, "resolved_weaknesses_count": 0,
                        "top_weaknesses": [], "skills": [],
                    }
                    res = await client.get("/api/v1/skills/overview")
                    assert res.status_code == 200 and res.json()["avg_proficiency_pct"] == 75.0

                # 2. List weaknesses
                with patch("app.api.v1.skills.get_candidate_weaknesses") as mock_list:
                    mock_list.return_value = [
                        CandidateWeakness(
                            id=uuid.uuid4(), user_id=uid, project_id=pid,
                            simulation_mode="arch", category="sec", topic="rbac",
                            severity="major", question_prompt="q", feedback="f",
                            resolved=False, created_at=now, updated_at=now,
                        )
                    ]
                    list_res = await client.get("/api/v1/skills/weaknesses?limit=10")
                    assert list_res.status_code == 200 and len(list_res.json()) == 1

                # 3. Resolve endpoint - 404 on not found
                with patch("app.api.v1.skills.resolve_weakness", return_value=None):
                    rand_id = uuid.uuid4()
                    bad_res = await client.patch(f"/api/v1/skills/weaknesses/{rand_id}/resolve")
                    assert bad_res.status_code == 404

                # 4. Evaluations endpoint
                eval_payload = RecordEvaluationRequest(
                    project_id=pid, simulation_mode="core_defense", category="architecture",
                    topic="modular_monolith", question_prompt="Why monolith?",
                    feedback="Good isolation.", passed=True, score=85.0,
                )
                with patch("app.api.v1.skills.record_evaluation_turn") as mock_rec:
                    skill_inst = UserSkill(
                        id=uuid.uuid4(), user_id=uid, category="architecture",
                        topic="modular_monolith", proficiency_score=85.0,
                        total_evaluations=1, passed_evaluations=1, failed_evaluations=0,
                        created_at=now, updated_at=now,
                    )
                    mock_rec.return_value = (skill_inst, None)
                    post_res = await client.post(
                        "/api/v1/skills/evaluations",
                        json=eval_payload.model_dump(mode="json"),
                    )
                    assert post_res.status_code == 201
                    assert post_res.json()["skill"]["proficiency_score"] == 85.0
                    assert post_res.json()["weakness"] is None
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(prev_overrides)

    asyncio.run(_impl())
