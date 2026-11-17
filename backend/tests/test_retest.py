"""Unit and API integration tests for Step 4.5a Targeted Re-Testing Engine & REST API."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.ai.retest_fallbacks import evaluate_retest_fallback, get_fallback_retest_question
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness, UserSkill
from app.services.retest_service import (
    create_targeted_retest_session,
    evaluate_retest_answer,
    get_eligible_retest_weaknesses,
)


def _make_mock_db(skills=None, weaknesses=None, single_weakness=None, single_skill=None):
    """Build mock AsyncSession returning configured entities based on query target."""
    mock_db = AsyncMock()

    async def _exec(stmt):
        res = MagicMock()
        s_str = str(stmt).lower()
        if "user_skills" in s_str:
            res.scalar_one_or_none.return_value = single_skill
            res.scalars.return_value.all.return_value = skills or []
        elif "candidate_weaknesses" in s_str:
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

    fallback_db = get_fallback_retest_question("database", "connection_pool")
    assert "connection" in fallback_db["question_text"].lower()

    strong_ans = (
        "We implement optimistic concurrency control using a version column in PostgreSQL. "
        "Each transaction executes select with version check. If a collision is detected, "
        "we use exponential backoff with jitter and retry with Redis distributed locks."
    )
    res_strong = evaluate_retest_fallback(strong_ans, "concurrency", "lost_updates")
    assert res_strong["passed"] is True and res_strong["score"] >= 70.0

    weak_ans = "I would just use a lock or restart the server."
    res_weak = evaluate_retest_fallback(weak_ans, "concurrency", "lost_updates")
    assert res_weak["passed"] is False and res_weak["score"] < 70.0


def test_get_eligible_retest_weaknesses():
    """Verify retrieval and filtering of candidate's unresolved weaknesses."""

    async def _impl():
        user_id = uuid.uuid4()
        p_id = uuid.uuid4()
        w1 = CandidateWeakness(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=p_id,
            simulation_mode="core_defense",
            category="concurrency",
            topic="race_conditions",
            severity="critical",
            question_prompt="How do you handle race conditions?",
            feedback="Missing transaction isolation.",
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_db = _make_mock_db(weaknesses=[w1])
        resp = await get_eligible_retest_weaknesses(
            session=mock_db, user_id=user_id, project_id=p_id
        )
        assert resp.total_eligible == 1
        assert resp.weaknesses[0].topic == "race_conditions"

    asyncio.run(_impl())


def test_create_targeted_retest_session():
    """Verify session creation maps weaknesses to targeted questions with constraints."""

    async def _impl():
        user_id = uuid.uuid4()
        w_id = uuid.uuid4()
        w1 = CandidateWeakness(
            id=w_id,
            user_id=user_id,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="database",
            topic="connection_starvation",
            severity="major",
            question_prompt="Why did you use direct connections?",
            feedback="Did not configure connection pool.",
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_db = _make_mock_db(weaknesses=[w1])
        session_resp = await create_targeted_retest_session(
            session=mock_db, user_id=user_id, weakness_ids=[w_id], max_questions=2
        )
        assert session_resp.total_questions == 1
        q = session_resp.questions[0]
        assert q.weakness_id == w_id and q.category == "database"
        assert len(q.question_text) > 20 and len(q.architectural_constraint) > 10

    asyncio.run(_impl())


def test_evaluate_retest_answer_pass():
    """Verify passing evaluation marks weakness resolved and reinforces skill."""

    async def _impl():
        user_id = uuid.uuid4()
        w_id = uuid.uuid4()
        weakness = CandidateWeakness(
            id=w_id,
            user_id=user_id,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="database",
            topic="connection_pooling",
            severity="major",
            question_prompt="Explain connection starvation.",
            feedback="Use connection pooling.",
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        skill = UserSkill(
            user_id=user_id,
            category="database",
            topic="connection_pooling",
            proficiency_score=50.0,
            total_evaluations=1,
            passed_evaluations=0,
            failed_evaluations=1,
        )

        mock_db = _make_mock_db(single_weakness=weakness, single_skill=skill)

        defense = (
            "We deploy PgBouncer in transaction mode with a shared pool of 80 connections "
            "to PostgreSQL. Individual workers do not hold direct connections, eliminating "
            "starvation and bounding connections to the 100 max limit."
        )

        mock_eval = {
            "passed": True,
            "score": 85.0,
            "feedback": "Solid architectural defense with bounded connection pool.",
            "key_improvements": ["PgBouncer transaction mode", "Bounded pool"],
            "remaining_gaps": [],
        }

        with patch(
            "app.services.retest_service.evaluate_targeted_retest_defense",
            new=AsyncMock(return_value=mock_eval),
        ):
            eval_resp = await evaluate_retest_answer(
                session=mock_db,
                user_id=user_id,
                session_id="retest-test-1",
                question_id="q-test-1",
                weakness_id=w_id,
                candidate_response=defense,
            )
            assert eval_resp.passed is True
            assert eval_resp.score >= 70.0
            assert eval_resp.weakness_resolved is True
            assert eval_resp.updated_proficiency == 60.0

    asyncio.run(_impl())


def test_evaluate_retest_idor_protection():
    """Verify that evaluating another user's weakness raises error."""

    async def _impl():
        user_id = uuid.uuid4()
        w_id = uuid.uuid4()
        mock_db = _make_mock_db(single_weakness=None, single_skill=None)

        try:
            await evaluate_retest_answer(
                session=mock_db,
                user_id=user_id,
                session_id="retest-idor",
                question_id="q-idor",
                weakness_id=w_id,
                candidate_response="Valid text longer than ten characters.",
            )
            assert False, "Should have raised ValueError"
        except ValueError as exc:
            assert "not found or does not belong" in str(exc)

    asyncio.run(_impl())


def test_retest_api_endpoints():
    """Verify full FastAPI REST API route contract for /api/v1/retest."""

    async def _impl():
        user_id = uuid.uuid4()
        test_user = User(
            id=user_id,
            email="retest_candidate@repodefense.dev",
        )
        w_id = uuid.uuid4()
        weakness = CandidateWeakness(
            id=w_id,
            user_id=user_id,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="concurrency",
            topic="race_conditions",
            severity="critical",
            question_prompt="Address race condition.",
            feedback="Need mutex or atomic CAS.",
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )

        app.dependency_overrides[get_current_user] = lambda: test_user
        mock_db = _make_mock_db(
            weaknesses=[weakness], single_weakness=weakness, single_skill=None
        )
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_eval = {
            "passed": True,
            "score": 80.0,
            "feedback": "Correct use of atomic compare-and-swap operations.",
            "key_improvements": ["Atomic CAS operations"],
            "remaining_gaps": [],
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            w_resp = await client.get("/api/v1/retest/weaknesses")
            assert w_resp.status_code == 200
            assert w_resp.json()["total_eligible"] == 1

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
                        "candidate_response": (
                            "We use atomic compare-and-swap operations and row-level locks with "
                            "timeouts to prevent race conditions during high concurrent txns."
                        ),
                    },
                )
                assert eval_resp.status_code == 200
                assert "score" in eval_resp.json() and "passed" in eval_resp.json()

        app.dependency_overrides.clear()

    asyncio.run(_impl())
