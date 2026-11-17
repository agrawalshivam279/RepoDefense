"""Unit and API contract tests for Step 4.4a Skill Progress & Improvement Telemetry."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness, UserSkill
from app.services.skill_progress import (
    _calculate_learning_streak,
    _calculate_mastery_status,
    get_user_progress_overview,
    get_user_progress_timeline,
)


def _make_mock_db(skills=None, weaknesses=None):
    """Build mock AsyncSession returning skills and weaknesses sequentially."""
    mock_db = AsyncMock()
    exec_res_skills = MagicMock()
    exec_res_skills.scalars.return_value.all.return_value = skills if skills is not None else []

    exec_res_weaknesses = MagicMock()
    exec_res_weaknesses.scalars.return_value.all.return_value = (
        weaknesses if weaknesses is not None else []
    )

    # First execute is skills, second is weaknesses, third is timeline skills
    mock_db.execute.side_effect = [exec_res_skills, exec_res_weaknesses, exec_res_skills]
    return mock_db


def test_mastery_status_classification():
    """Verify standard proficiency threshold classification."""
    assert _calculate_mastery_status(90.0) == "mastered"
    assert _calculate_mastery_status(80.0) == "mastered"
    assert _calculate_mastery_status(75.0) == "proficient"
    assert _calculate_mastery_status(65.0) == "proficient"
    assert _calculate_mastery_status(55.0) == "improving"
    assert _calculate_mastery_status(50.0) == "improving"
    assert _calculate_mastery_status(40.0) == "needs_focus"


def test_learning_streak_calculation():
    """Verify consecutive learning streak computation."""
    today = datetime.now(timezone.utc).date()
    # Streak active: today, yesterday, 2 days ago
    dates_active = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert _calculate_learning_streak(dates_active) == 3
    # Streak active ending yesterday: yesterday, 2 days ago
    assert _calculate_learning_streak({today - timedelta(days=1), today - timedelta(days=2)}) == 2
    # Broken streak: 3 days ago, 4 days ago
    assert _calculate_learning_streak({today - timedelta(days=3), today - timedelta(days=4)}) == 0
    # Empty dates
    assert _calculate_learning_streak(set()) == 0


def test_empty_user_progress_overview():
    """Verify empty state returns valid neutral response with zero counts."""
    async def _impl():
        user_id = uuid.uuid4()
        mock_db = _make_mock_db(skills=[], weaknesses=[])

        overview = await get_user_progress_overview(mock_db, user_id)

        assert overview.overall_proficiency == 0.0
        assert overview.total_evaluations == 0
        assert overview.total_passed == 0
        assert overview.overall_pass_rate_pct == 0.0
        assert overview.active_skills_count == 0
        assert overview.mastered_skills_count == 0
        assert overview.learning_streak_days == 0
        assert overview.weakness_velocity.total_identified == 0
        assert overview.weakness_velocity.total_resolved == 0
        assert overview.weakness_velocity.resolution_rate_pct == 0.0
        assert overview.weakness_velocity.average_resolution_hours is None
        assert overview.category_deltas == []
        assert overview.top_improved_topics == []
        assert overview.needs_focus_topics == []

    asyncio.run(_impl())


def test_populated_user_progress_overview():
    """Verify aggregated metrics, velocity, category deltas, and focus lists."""
    async def _impl():
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        skill_master = UserSkill(
            id=uuid.uuid4(),
            user_id=user_id,
            category="scalability",
            topic="connection_pooling",
            proficiency_score=85.0,
            total_evaluations=10,
            passed_evaluations=9,
            failed_evaluations=1,
            last_evaluated_at=now,
        )
        skill_weak = UserSkill(
            id=uuid.uuid4(),
            user_id=user_id,
            category="concurrency",
            topic="lost_updates",
            proficiency_score=45.0,
            total_evaluations=4,
            passed_evaluations=1,
            failed_evaluations=3,
            last_evaluated_at=now - timedelta(days=1),
        )

        w1 = CandidateWeakness(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="scalability",
            topic="connection_pooling",
            severity="critical",
            question_prompt="q",
            feedback="f",
            resolved=True,
            created_at=now - timedelta(hours=6),
            resolved_at=now - timedelta(hours=2),
        )
        w2 = CandidateWeakness(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="concurrency",
            topic="lost_updates",
            severity="major",
            question_prompt="q",
            feedback="f",
            resolved=False,
            created_at=now - timedelta(hours=10),
            resolved_at=None,
        )

        mock_db = _make_mock_db(skills=[skill_master, skill_weak], weaknesses=[w1, w2])

        overview = await get_user_progress_overview(mock_db, user_id)

        assert overview.overall_proficiency == 65.0
        assert overview.total_evaluations == 14
        assert overview.total_passed == 10
        assert overview.overall_pass_rate_pct == 71.4
        assert overview.active_skills_count == 2
        assert overview.mastered_skills_count == 1

        # Velocity
        assert overview.weakness_velocity.total_identified == 2
        assert overview.weakness_velocity.total_resolved == 1
        assert overview.weakness_velocity.resolution_rate_pct == 50.0
        assert overview.weakness_velocity.critical_total == 1
        assert overview.weakness_velocity.critical_resolved == 1
        assert overview.weakness_velocity.major_total == 1
        assert overview.weakness_velocity.major_resolved == 0
        assert overview.weakness_velocity.average_resolution_hours == 4.0

        # Categories
        cat_map = {c.category: c for c in overview.category_deltas}
        assert "scalability" in cat_map and "concurrency" in cat_map
        assert cat_map["scalability"].status == "mastered"
        assert cat_map["scalability"].pass_rate_pct == 90.0
        assert cat_map["concurrency"].status == "needs_focus"
        assert cat_map["concurrency"].pass_rate_pct == 25.0

        # Top / Needs Focus
        assert len(overview.top_improved_topics) == 2
        assert overview.top_improved_topics[0].topic == "connection_pooling"
        assert len(overview.needs_focus_topics) == 1
        assert overview.needs_focus_topics[0].topic == "lost_updates"

    asyncio.run(_impl())


def test_timeline_points_aggregation():
    """Verify daily timeline generation from user skill evaluation dates."""
    async def _impl():
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        skill1 = UserSkill(
            id=uuid.uuid4(),
            user_id=user_id,
            category="security",
            topic="auth_jwt",
            proficiency_score=80.0,
            total_evaluations=5,
            passed_evaluations=4,
            failed_evaluations=1,
            last_evaluated_at=now,
        )

        mock_db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalars.return_value.all.return_value = [skill1]
        mock_db.execute.return_value = exec_res

        timeline = await get_user_progress_timeline(mock_db, user_id, days=7)
        assert len(timeline) == 1
        assert timeline[0].date == now.strftime("%Y-%m-%d")
        assert timeline[0].average_proficiency == 80.0
        assert timeline[0].evaluations_count == 5
        assert timeline[0].passed_count == 4

    asyncio.run(_impl())


def test_progress_api_endpoints():
    """Verify HTTP GET /api/v1/progress/overview, /timeline, /categories."""
    async def _impl():
        user_id = uuid.uuid4()
        mock_user = User(
            id=user_id,
            email="developer@example.com",
        )

        skill = UserSkill(
            id=uuid.uuid4(),
            user_id=user_id,
            category="architecture",
            topic="modular_monolith",
            proficiency_score=90.0,
            total_evaluations=6,
            passed_evaluations=6,
            failed_evaluations=0,
            last_evaluated_at=datetime.now(timezone.utc),
        )

        def _get_mock_db():
            mock_db = AsyncMock()

            async def _exec(stmt):
                res = MagicMock()
                if "candidate_weaknesses" in str(stmt):
                    res.scalars.return_value.all.return_value = []
                else:
                    res.scalars.return_value.all.return_value = [skill]
                return res

            mock_db.execute.side_effect = _exec
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = _get_mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Overview
                res = await client.get("/api/v1/progress/overview")
                assert res.status_code == 200
                data = res.json()
                assert data["overall_proficiency"] == 90.0
                assert data["total_evaluations"] == 6
                assert data["mastered_skills_count"] == 1

                # 2. Timeline
                res_tl = await client.get("/api/v1/progress/timeline?days=14")
                assert res_tl.status_code == 200
                tl_data = res_tl.json()
                assert isinstance(tl_data, list)
                assert len(tl_data) == 1

                # 3. Categories
                res_cat = await client.get("/api/v1/progress/categories")
                assert res_cat.status_code == 200
                cat_data = res_cat.json()
                assert len(cat_data) == 1
                assert cat_data[0]["category"] == "architecture"
                assert cat_data[0]["status"] == "mastered"
        finally:
            app.dependency_overrides.clear()

    asyncio.run(_impl())
