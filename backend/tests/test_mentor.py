"""Unit and API contract tests for Step 4.2a Mentor Teaching Content Engine & REST API."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.ai.mentor_generator import (
    _build_deterministic_mentor_explanation,
    generate_mentor_explanation,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import User
from app.models.skill import CandidateWeakness
from app.schemas.mentor import MentorExplanationResponse


def _make_mock_db(scalar_return=None):
    """Build mock AsyncSession returning specified scalar."""
    mock_db = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = scalar_return
    mock_db.execute.return_value = exec_res
    return mock_db


def test_mentor_generator_deterministic_fallbacks():
    """Verify fallback synthesizes rich architectural explanations and code snippets."""
    # 1. Database pooling topic
    resp_db = _build_deterministic_mentor_explanation(
        category="scalability", topic="connection_pooling"
    )
    assert isinstance(resp_db, MentorExplanationResponse)
    assert "pooling" in resp_db.architectural_risk.lower()
    assert len(resp_db.code_examples) >= 1
    assert "psycopg2" in resp_db.code_examples[0].before_code
    assert "AsyncSession" in resp_db.code_examples[0].after_code
    assert len(resp_db.key_takeaways) >= 2
    assert resp_db.socratic_followup != ""

    # 2. Concurrency topic
    resp_conc = _build_deterministic_mentor_explanation(
        category="concurrency", topic="race_condition_locks"
    )
    assert "lost update" in resp_conc.architectural_risk.lower()
    assert "optimistic" in resp_conc.core_concept.lower()

    # 3. Cache stampede topic
    resp_cache = _build_deterministic_mentor_explanation(
        category="scalability", topic="cache_stampede"
    )
    assert "thundering herd" in resp_cache.code_examples[0].before_code.lower()

    # 4. Generic / Other topic
    resp_gen = _build_deterministic_mentor_explanation(
        category="architecture", topic="domain_service_coupling"
    )
    assert resp_gen.category == "architecture"
    assert resp_gen.code_examples[0].language == "python"


def test_mentor_generator_with_mock_litellm():
    """Verify structured response parsing from LiteLLM JSON output."""
    async def _impl():
        mock_payload = {
            "category": "security",
            "topic": "tenant_isolation_idor",
            "architectural_risk": "Missing tenant predicate allows cross-tenant data access.",
            "core_concept": "Multi-Tenant Row-Level Isolation",
            "mentor_advice": "Always filter database queries with user_id == current_user.id.",
            "code_examples": [
                {
                    "title": "Enforce Tenant Predicate",
                    "language": "python",
                    "file_context": "backend/app/api/v1/projects.py",
                    "before_code": "stmt = select(Project).where(Project.id == pid)",
                    "after_code": (
                        "stmt = select(Project).where(Project.id == pid, Project.user_id == uid)"
                    ),
                    "explanation": "Adding user_id eliminates IDOR vulnerabilities.",
                }
            ],
            "key_takeaways": ["Never trust client-supplied entity IDs blindly."],
            "socratic_followup": "How would you write an automated regression test for IDOR?",
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_payload)
        mock_litellm_resp = MagicMock()
        mock_litellm_resp.choices = [mock_choice]

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_resp

            result = await generate_mentor_explanation(
                category="security",
                topic="tenant_isolation_idor",
                llm_api_key="test-key",
                llm_base_url="https://api.openai.com/v1",
            )

            assert result.category == "security"
            assert result.topic == "tenant_isolation_idor"
            assert len(result.code_examples) == 1
            assert "Project.user_id == uid" in result.code_examples[0].after_code
            assert mock_acompletion.called

    asyncio.run(_impl())


def test_mentor_generator_error_falls_back_cleanly():
    """Verify LiteLLM timeout or error gracefully invokes deterministic fallback."""
    async def _impl():
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.side_effect = TimeoutError("LLM call timed out")

            result = await generate_mentor_explanation(
                category="scalability",
                topic="connection_pooling",
                llm_api_key="test-key",
                llm_base_url="https://api.openai.com/v1",
            )

            assert isinstance(result, MentorExplanationResponse)
            assert result.category == "scalability"
            assert len(result.code_examples) >= 1
            assert "psycopg2" in result.code_examples[0].before_code

    asyncio.run(_impl())


def test_mentor_rest_endpoints():
    """Verify /api/v1/mentor/explain and /explanations/{id} with auth, IDOR, and fallback."""
    async def _impl():
        transport = ASGITransport(app=app)

        # 1. Anonymous access is rejected
        async with AsyncClient(transport=transport, base_url="http://test") as anon:
            resp = await anon.post("/api/v1/mentor/explain", json={"topic": "testing"})
            assert resp.status_code in (401, 403)

        uid = uuid.uuid4()
        user = User(id=uid, email="candidate@repodefense.dev")
        now = datetime.now(timezone.utc)
        weakness = CandidateWeakness(
            id=uuid.uuid4(),
            user_id=uid,
            project_id=uuid.uuid4(),
            simulation_mode="core_defense",
            category="concurrency",
            topic="race_condition_locks",
            severity="major",
            question_prompt="How do you prevent lost updates on bank transfers?",
            candidate_response="I just do account.balance += amount and save.",
            feedback="Candidate neglected atomic locking or version check.",
            resolved=False,
            created_at=now,
            updated_at=now,
        )

        mock_db = _make_mock_db(scalar_return=weakness)
        prev_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 2. POST /explain with inline topic & category
                res_inline = await client.post(
                    "/api/v1/mentor/explain",
                    json={
                        "category": "scalability",
                        "topic": "connection_pooling",
                        "language": "python",
                    },
                )
                assert res_inline.status_code == 200
                data_inline = res_inline.json()
                assert data_inline["topic"] == "connection_pooling"
                assert len(data_inline["code_examples"]) >= 1

                # 3. POST /explain with weakness_id
                res_weakness = await client.post(
                    "/api/v1/mentor/explain",
                    json={"weakness_id": str(weakness.id)},
                )
                assert res_weakness.status_code == 200
                data_weakness = res_weakness.json()
                assert data_weakness["topic"] == "race_condition_locks"
                assert "concurrency" in data_weakness["category"].lower()

                # 4. POST /explain with non-existent or unowned weakness_id (IDOR defense)
                mock_db.execute.return_value.scalar_one_or_none.return_value = None
                res_unauthorized = await client.post(
                    "/api/v1/mentor/explain",
                    json={"weakness_id": str(uuid.uuid4())},
                )
                assert res_unauthorized.status_code == 404

                # 5. GET /explanations/{weakness_id}
                mock_db.execute.return_value.scalar_one_or_none.return_value = weakness
                res_get = await client.get(f"/api/v1/mentor/explanations/{weakness.id}")
                assert res_get.status_code == 200
                data_get = res_get.json()
                assert data_get["topic"] == "race_condition_locks"

                # 6. GET /explanations/{weakness_id} unowned (404 IDOR check)
                mock_db.execute.return_value.scalar_one_or_none.return_value = None
                res_get_unauth = await client.get(f"/api/v1/mentor/explanations/{uuid.uuid4()}")
                assert res_get_unauth.status_code == 404

                # 7. POST /explain empty body (422 Unprocessable Entity)
                res_invalid = await client.post("/api/v1/mentor/explain", json={})
                assert res_invalid.status_code == 422
        finally:
            app.dependency_overrides = prev_overrides

    asyncio.run(_impl())
