"""Unit and API tests for Step 4.3a Mentor Mode Mini Challenges Engine & REST API."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.ai.challenge_fallbacks import build_fallback_challenge, build_fallback_evaluation
from app.ai.challenge_generator import evaluate_mini_challenge, generate_mini_challenge
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness
from app.schemas.challenge import (
    ChallengeEvaluationResponse,
    MiniChallengeDifficulty,
    MiniChallengeResponse,
)


def _make_mock_db(scalar_return=None):
    """Build mock AsyncSession returning specified scalar."""
    mock_db = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = scalar_return
    mock_db.execute.return_value = exec_res
    return mock_db


def test_challenge_fallbacks_generation():
    """Verify deterministic fallback generates targeted mini-challenges with requirements."""
    # 1. Connection pooling topic
    resp_pool = build_fallback_challenge(
        category="scalability", topic="connection_pooling"
    )
    assert isinstance(resp_pool, MiniChallengeResponse)
    assert "connection" in resp_pool.title.lower()
    assert len(resp_pool.requirements) >= 2
    assert len(resp_pool.hints) >= 2
    assert "asyncpg" in (resp_pool.starter_code or "")

    # 2. Concurrency lock topic
    resp_lock = build_fallback_challenge(
        category="concurrency", topic="race_condition_locks"
    )
    assert "lost update" in resp_lock.title.lower()
    assert "with_for_update" in " ".join(resp_lock.hints)

    # 3. Cache stampede topic
    resp_cache = build_fallback_challenge(
        category="caching", topic="cache_stampede"
    )
    assert "stampede" in resp_cache.title.lower()
    assert "mutex" in " ".join(resp_cache.requirements).lower()

    # 4. Generic topic
    resp_generic = build_fallback_challenge(
        category="architecture", topic="rate_limiting"
    )
    assert "rate limiting" in resp_generic.title.lower()
    assert len(resp_generic.requirements) >= 2


def test_challenge_fallbacks_evaluation():
    """Verify deterministic fallback grades solutions accurately based on defense heuristics."""
    challenge_id = uuid.uuid4()
    reqs = ["Use connection pool", "Add timeout"]

    strong_solution = (
        "async def handle(pool):\n"
        "    async with asyncio.timeout(2.0):\n"
        "        async with pool.acquire() as conn:\n"
        "            return await conn.fetch('SELECT 1')"
    )
    eval_pass = build_fallback_evaluation(challenge_id, strong_solution, reqs)
    assert isinstance(eval_pass, ChallengeEvaluationResponse)
    assert eval_pass.passed is False
    assert eval_pass.score == 65.0
    assert len(eval_pass.strengths) >= 2
    assert "offline" in eval_pass.critique.lower()
    assert eval_pass.model_solution != ""

    weak_solution = "def handle(): pass"
    eval_fail = build_fallback_evaluation(challenge_id, weak_solution, reqs)
    assert eval_fail.passed is False
    assert eval_fail.score == 45.0
    assert len(eval_fail.missing_elements) >= 1


def test_challenge_generator_with_mock_litellm():
    """Verify LiteLLM parsing for both challenge synthesis and evaluation."""
    async def _impl():
        # Mock challenge generation response
        mock_gen_choice = MagicMock()
        mock_gen_choice.message.content = json.dumps({
            "title": "Custom Auth Middleware Lockout",
            "scenario": "A custom token validation middleware leaks connections under load.",
            "starter_code": "async def auth_middleware(req): ...",
            "requirements": ["Bound token cache", "Isolate DB edge queries"],
            "hints": ["Use Redis TTL", "Catch connection errors"],
        })
        mock_gen_resp = MagicMock(choices=[mock_gen_choice])

        # Mock evaluation response
        mock_eval_choice = MagicMock()
        mock_eval_choice.message.content = json.dumps({
            "passed": True,
            "score": 90.0,
            "strengths": ["Clean token cache bounding", "Safe fallback on timeout"],
            "missing_elements": [],
            "critique": "Outstanding architectural refactoring.",
            "model_solution": "async def auth_middleware(req): pass",
        })
        mock_eval_resp = MagicMock(choices=[mock_eval_choice])

        with patch("app.ai.challenge_generator.acompletion") as mock_acompletion:
            # 1. Test generate_mini_challenge
            mock_acompletion.return_value = mock_gen_resp
            gen_result = await generate_mini_challenge(
                category="security",
                topic="auth_middleware_leak",
                difficulty=MiniChallengeDifficulty.ADVANCED,
                llm_api_key="mock-key",
            )
            assert gen_result.title == "Custom Auth Middleware Lockout"
            assert len(gen_result.requirements) == 2
            assert gen_result.difficulty == MiniChallengeDifficulty.ADVANCED

            # 2. Test evaluate_mini_challenge
            mock_acompletion.return_value = mock_eval_resp
            eval_result = await evaluate_mini_challenge(
                challenge_id=uuid.uuid4(),
                category="security",
                topic="auth_middleware_leak",
                scenario="Scenario text",
                requirements=["Req 1"],
                candidate_solution="My production solution",
                llm_api_key="mock-key",
            )
            assert eval_result.passed is True
            assert eval_result.score == 90.0
            assert "Outstanding" in eval_result.critique

    asyncio.run(_impl())


def test_challenge_api_generate_and_idor():
    """Verify POST /challenges/generate and IDOR isolation."""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    user = User(id=user_id, email="dev@repodefense.com", created_at=datetime.now(timezone.utc))

    unowned_weakness = CandidateWeakness(
        id=uuid.uuid4(),
        user_id=other_user_id,
        project_id=uuid.uuid4(),
        category="scalability",
        topic="connection_starvation",
        severity="major",
        question_prompt="How do you handle pooling?",
        candidate_response="I open a new connection.",
        feedback="Missing connection pool.",
        resolved=False,
    )

    async def _run():
        transport = ASGITransport(app=app)
        orig_overrides = dict(app.dependency_overrides)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: user
            with patch("app.ai.challenge_generator.acompletion", side_effect=Exception("offline")):
                try:
                    # 1. Success with inline topic
                    mock_db = _make_mock_db(scalar_return=None)
                    app.dependency_overrides[get_db] = lambda: mock_db
                    resp = await client.post(
                        "/api/v1/mentor/challenges/generate",
                        json={"category": "scalability", "topic": "connection_pooling"},
                    )
                    assert resp.status_code == 200, resp.text
                    assert resp.json()["topic"] == "connection_pooling"

                    # 2. IDOR rejection: accessing unowned weakness returns 404
                    mock_db_idor = _make_mock_db(scalar_return=None)
                    app.dependency_overrides[get_db] = lambda: mock_db_idor
                    resp_idor = await client.post(
                        "/api/v1/mentor/challenges/generate",
                        json={"weakness_id": str(unowned_weakness.id)},
                    )
                    assert resp_idor.status_code == 404
                    assert "not found or access denied" in resp_idor.json()["detail"].lower()
                finally:
                    app.dependency_overrides = orig_overrides

    asyncio.run(_run())


def test_challenge_api_evaluate_and_resolution():
    """Verify POST /challenges/evaluate resolves linked CandidateWeakness when passed."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email="dev@repodefense.com", created_at=datetime.now(timezone.utc))
    weakness_id = uuid.uuid4()
    owned_weakness = CandidateWeakness(
        id=weakness_id,
        user_id=user_id,
        project_id=uuid.uuid4(),
        category="scalability",
        topic="connection_pooling",
        severity="major",
        question_prompt="How do you pool DB connections?",
        candidate_response="I create a new connection per request.",
        feedback="Lacks connection pooling.",
        resolved=False,
    )

    async def _run():
        transport = ASGITransport(app=app)
        orig_overrides = dict(app.dependency_overrides)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: user
            mock_db = _make_mock_db(scalar_return=owned_weakness)
            app.dependency_overrides[get_db] = lambda: mock_db

            try:
                # 1. Topic mismatch validation raises 400
                mismatch_resp = await client.post(
                    "/api/v1/mentor/challenges/evaluate",
                    json={
                        "challenge_id": str(uuid.uuid4()),
                        "weakness_id": str(weakness_id),
                        "category": "scalability",
                        "topic": "caching_stampede",
                        "scenario": "Mismatch scenario",
                        "requirements": ["Req 1"],
                        "candidate_solution": "def test_solution(): pass",
                    },
                )
                assert mismatch_resp.status_code == 400
                assert "does not match" in mismatch_resp.json()["detail"].lower()

                # 2. Passing evaluation resolves weakness
                passing_eval = ChallengeEvaluationResponse(
                    challenge_id=uuid.uuid4(),
                    passed=True,
                    score=90.0,
                    strengths=["Implemented pool acquire"],
                    missing_elements=[],
                    critique="Excellent defense.",
                    model_solution="async def handle(): pass",
                )
                with (
                    patch("app.api.v1.mentor.resolve_weakness", new_callable=AsyncMock) as m_res,
                    patch(
                        "app.api.v1.mentor.evaluate_mini_challenge", new_callable=AsyncMock
                    ) as m_eval,
                ):
                    m_eval.return_value = passing_eval
                    m_res.return_value = owned_weakness

                    resp = await client.post(
                        "/api/v1/mentor/challenges/evaluate",
                        json={
                            "challenge_id": str(uuid.uuid4()),
                            "weakness_id": str(weakness_id),
                            "category": "scalability",
                            "topic": "connection_pooling",
                            "scenario": "Exhaustion under load.",
                            "requirements": ["Bound pool", "Add timeout"],
                            "candidate_solution": "async def handle(): pass",
                        },
                    )
                    assert resp.status_code == 200, resp.text
                    data = resp.json()
                    assert data["passed"] is True
                    assert data["weakness_updated"] is True
                    m_res.assert_awaited_once()
            finally:
                app.dependency_overrides = orig_overrides

    asyncio.run(_run())
