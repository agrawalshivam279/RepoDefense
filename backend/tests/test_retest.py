"""Unit and API integration tests for Step 4.5a Targeted Re-Testing Engine & REST API."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.retest_fallbacks import evaluate_retest_fallback, get_fallback_retest_question
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness, UserSkill
from app.services.retest_service import (
    RetestNotFoundError,
    _store_active_question,
    create_targeted_retest_session,
    evaluate_retest_answer,
    get_eligible_retest_weaknesses,
)


def _make_mock_db(skills=None, weaknesses=None, single_weakness=None, single_skill=None):
    """Build mock AsyncSession returning configured entities based on query target."""
    mock_db = AsyncMock()

    async def _exec(stmt):
        res = MagicMock()
        s = str(stmt).lower()
        if "user_skills" in s:
            res.scalar_one_or_none.return_value = single_skill
            res.scalars.return_value.all.return_value = skills or []
        elif "candidate_weaknesses" in s:
            res.scalar_one_or_none.return_value = single_weakness
            res.scalars.return_value.all.return_value = weaknesses or []
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    mock_db.execute.side_effect = _exec
    return mock_db


def test_retest_fallbacks():
    """Verify deterministic fallback question generation and heuristic evaluation."""
    fallback_cc = get_fallback_retest_question("concurrency", "lost_updates")
    assert "concurrency" in fallback_cc["question_text"].lower()
    assert "10,000" in fallback_cc["architectural_constraint"]
    assert "connection" in get_fallback_retest_question("database", "pool")["question_text"].lower()

    # Keyword-stuffed answer under 30 words must fail
    kw_only = "lock mutex cache redis pool queue partition"
    assert evaluate_retest_fallback(kw_only, "concurrency", "lost_updates")["passed"] is False

    strong_ans = (
        "We implement optimistic concurrency control using a version column in PostgreSQL. "
        "Each transaction executes select with version check. If a collision is detected, "
        "we use exponential backoff with jitter and retry with Redis distributed locks."
    )
    res_strong = evaluate_retest_fallback(strong_ans, "concurrency", "lost_updates")
    assert res_strong["passed"] is True and res_strong["score"] >= 70.0

    weak_ans = "I would just use a lock or restart the server."
    assert evaluate_retest_fallback(weak_ans, "concurrency", "lost_updates")["passed"] is False


def test_get_eligible_retest_weaknesses():
    """Verify retrieval and filtering of candidate's unresolved weaknesses."""

    async def _impl():
        user_id = uuid.uuid4()
        w1 = CandidateWeakness(
            id=uuid.uuid4(), user_id=user_id, project_id=uuid.uuid4(),
            simulation_mode="core", category="concurrency", topic="race_conditions",
            severity="critical", question_prompt="q", feedback="f", resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_db = _make_mock_db(weaknesses=[w1])
        resp = await get_eligible_retest_weaknesses(session=mock_db, user_id=user_id)
        assert resp.total_eligible == 1 and resp.weaknesses[0].topic == "race_conditions"

    asyncio.run(_impl())


def test_create_targeted_retest_session():
    """Verify session creation maps weaknesses to targeted questions with constraints."""

    async def _impl():
        user_id, w_id = uuid.uuid4(), uuid.uuid4()
        w1 = CandidateWeakness(
            id=w_id, user_id=user_id, project_id=uuid.uuid4(), simulation_mode="core",
            category="database", topic="starvation", severity="major", question_prompt="q",
            feedback="f", resolved=False, created_at=datetime.now(timezone.utc),
        )
        mock_db = _make_mock_db(weaknesses=[w1])
        with patch("app.ai.retest_generator.settings.FREELLMAPI_API_KEY", ""):
            resp = await create_targeted_retest_session(
                session=mock_db, user_id=user_id, weakness_ids=[w_id], max_questions=2
            )
        assert resp.total_questions == 1
        assert resp.questions[0].weakness_id == w_id and resp.questions[0].category == "database"

    asyncio.run(_impl())


def test_evaluate_retest_answer_pass():
    """Verify passing evaluation marks weakness resolved and reinforces skill."""

    async def _impl():
        user_id, w_id = uuid.uuid4(), uuid.uuid4()
        weakness = CandidateWeakness(
            id=w_id, user_id=user_id, project_id=uuid.uuid4(), simulation_mode="core",
            category="database", topic="pool", severity="major", question_prompt="q",
            feedback="f", resolved=False, created_at=datetime.now(timezone.utc),
        )
        skill = UserSkill(
            user_id=user_id, category="database", topic="pool", proficiency_score=50.0,
            total_evaluations=1, passed_evaluations=0, failed_evaluations=1,
        )
        mock_db = _make_mock_db(single_weakness=weakness, single_skill=skill)
        _store_active_question(
            "q-test-1",
            {
                "session_id": "s-1", "user_id": user_id, "weakness_id": w_id,
                "category": "database", "topic": "pool", "question_text": "q",
                "constraint": "c", "rubric": "r",
            },
        )
        defense = (
            "We deploy PgBouncer in transaction mode with a shared pool of 80 connections "
            "to PostgreSQL. Individual workers do not hold direct connections, eliminating "
            "starvation and bounding connections to the 100 max limit."
        )
        mock_eval = {
            "passed": True, "score": 85.0, "feedback": "Solid defense.",
            "key_improvements": ["PgBouncer mode"], "remaining_gaps": [],
        }
        with patch(
            "app.services.retest_service.evaluate_targeted_retest_defense",
            new=AsyncMock(return_value=mock_eval),
        ):
            resp = await evaluate_retest_answer(
                session=mock_db, user_id=user_id, session_id="s-1",
                question_id="q-test-1", weakness_id=w_id, candidate_response=defense,
            )
            assert resp.passed is True and resp.score >= 70.0
            assert resp.weakness_resolved is True and resp.updated_proficiency == 60.0

    asyncio.run(_impl())


def test_evaluate_retest_idor_protection():
    """Verify that evaluating a non-owned weakness raises RetestNotFoundError."""

    async def _impl():
        user_id, w_id = uuid.uuid4(), uuid.uuid4()
        mock_db = _make_mock_db(single_weakness=None, single_skill=None)
        with pytest.raises(RetestNotFoundError):
            await evaluate_retest_answer(
                session=mock_db, user_id=user_id, session_id="s-idor",
                question_id="q-idor", weakness_id=w_id,
                candidate_response="Valid text longer than ten chars.",
            )

    asyncio.run(_impl())


def test_retest_api_endpoints():
    """Verify full FastAPI REST API route contract for /api/v1/retest."""

    async def _impl():
        user_id, w_id = uuid.uuid4(), uuid.uuid4()
        test_user = User(id=user_id, email="retest@repodefense.dev")
        weakness = CandidateWeakness(
            id=w_id, user_id=user_id, project_id=uuid.uuid4(), simulation_mode="core",
            category="concurrency", topic="race", severity="critical", question_prompt="q",
            feedback="f", resolved=False, created_at=datetime.now(timezone.utc),
        )
        saved = dict(app.dependency_overrides)
        try:
            app.dependency_overrides[get_current_user] = lambda: test_user
            mock_db = _make_mock_db(
                weaknesses=[weakness], single_weakness=weakness, single_skill=None
            )
            app.dependency_overrides[get_db] = lambda: mock_db
            mock_eval = {
                "passed": True, "score": 80.0, "feedback": "Good.",
                "key_improvements": ["CAS"], "remaining_gaps": [],
            }
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                w_resp = await client.get("/api/v1/retest/weaknesses")
                assert w_resp.status_code == 200 and w_resp.json()["total_eligible"] == 1

                with patch("app.ai.retest_generator.settings.FREELLMAPI_API_KEY", ""):
                    sess_resp = await client.post(
                        "/api/v1/retest/session",
                        json={"weakness_ids": [str(w_id)], "max_questions": 2},
                    )
                assert sess_resp.status_code == 201
                q_id = sess_resp.json()["questions"][0]["question_id"]

                with patch(
                    "app.services.retest_service.evaluate_targeted_retest_defense",
                    new=AsyncMock(return_value=mock_eval),
                ):
                    eval_resp = await client.post(
                        "/api/v1/retest/evaluate",
                        json={
                            "session_id": sess_resp.json()["session_id"],
                            "question_id": q_id,
                            "weakness_id": str(w_id),
                            "candidate_response": "We use atomic compare-and-swap operations.",
                        },
                    )
                assert eval_resp.status_code == 200
                assert eval_resp.json()["passed"] is True
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved)

    asyncio.run(_impl())
