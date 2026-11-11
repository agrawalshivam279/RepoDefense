"""Regression tests for defense router contract alignment and LLM override forwarding."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import create_defense_session, defense_store
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.analysis import Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.defense import EvaluationOutput
from app.schemas.question import GroundedQuestion, QuestionCategory, QuestionGenerationInput
from tests.test_auth import create_test_jwt


@pytest.mark.anyio
async def test_defense_start_grounds_evidence_and_forwards_overrides():
    """Verify POST /defense/start queries Evidence/Snapshot properly and forwards overrides."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    email = f"defense_start_{uuid.uuid4().hex[:6]}@repodefense.dev"
    mock_user = User(id=user_id, email=email)
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="start-repo",
        github_url="https://github.com/test/start-repo",
    )
    mock_snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        project_id=project_id,
        commit_hash="a" * 40,
        summary=json.dumps({
            "narrative": "Async FastAPI service with PostgreSQL",
            "architectural_style": "Modular Monolith",
        }),
    )
    mock_evidence = Evidence(
        id=evidence_id,
        project_id=project_id,
        evidence_type="database",
        title="Postgres Connection Pool",
        description="Async SQLAlchemy session engine",
        file_path="app/core/database.py",
        start_line=10,
        end_line=35,
    )

    async with AsyncSessionLocal() as db_session:
        db_session.add_all([mock_user, mock_project, mock_snapshot, mock_evidence])
        await db_session.commit()

    generated_q = GroundedQuestion(
        id="q-start-1",
        category=QuestionCategory.SCALABILITY,
        question_text="Why size the asyncpg pool this way?",
        context_hint="app/core/database.py lines 10-35",
        cited_evidence_ids=[str(evidence_id)],
        cited_files=["app/core/database.py"],
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    session_id = None

    try:
        token = create_test_jwt(user_id, email)
        headers = {"Authorization": f"Bearer {token}"}

        with patch(
            "app.api.v1.defense.generate_grounded_questions",
            new_callable=AsyncMock,
            return_value=[generated_q],
        ) as mock_gen:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                res = await ac.post(
                    f"/api/v1/projects/{project_id}/defense/start",
                    json={
                        "num_questions": 2,
                        "custom_categories": ["database"],
                        "model": "custom/start-model",
                        "api_key": "start-secret-key",
                        "base_url": "https://start.llm.local",
                    },
                    headers=headers,
                )

        assert res.status_code == 201
        body = res.json()
        session_id = body["session_id"]
        assert body["project_id"] == str(project_id)
        assert body["total_questions"] == 1

        mock_gen.assert_awaited_once()
        kwargs = mock_gen.await_args.kwargs
        gen_input = kwargs["input_data"]
        assert isinstance(gen_input, QuestionGenerationInput)
        assert gen_input.requested_count == 2
        assert gen_input.summary_narrative == "Async FastAPI service with PostgreSQL"
        assert gen_input.architectural_style == "Modular Monolith"
        assert len(gen_input.evidence_items) == 1
        assert gen_input.evidence_items[0].title == "Postgres Connection Pool"
        assert kwargs["model"] == "custom/start-model"
        assert kwargs["api_key"] == "start-secret-key"
        assert kwargs["base_url"] == "https://start.llm.local"
    finally:
        app.dependency_overrides.clear()
        if session_id:
            await defense_store.delete(session_id)
        async with AsyncSessionLocal() as db_session:
            db_user = await db_session.get(User, user_id)
            if db_user:
                await db_session.delete(db_user)
                await db_session.commit()


@pytest.mark.anyio
async def test_defense_turn_forwards_llm_overrides():
    """Verify POST /defense/sessions/{id}/turn forwards model/api_key/base_url overrides."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    email = f"defense_turn_{uuid.uuid4().hex[:6]}@repodefense.dev"
    mock_user = User(id=user_id, email=email)
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="turn-repo",
        github_url="https://github.com/test/turn-repo",
    )
    async with AsyncSessionLocal() as db_session:
        db_session.add_all([mock_user, mock_project])
        await db_session.commit()

    q1 = GroundedQuestion(
        id="q-turn-1",
        category=QuestionCategory.RELIABILITY,
        question_text="How are retries bounded?",
        context_hint="app/ai/llm.py",
        cited_evidence_ids=["ev-1"],
        cited_files=["app/ai/llm.py"],
    )
    session = await create_defense_session(str(project_id), [q1], store=defense_store)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        token = create_test_jwt(user_id, email)
        headers = {"Authorization": f"Bearer {token}"}
        mock_eval_out = EvaluationOutput(
            passed_initial_defense=True,
            depth_score=8,
            grounding_verified=True,
            is_vague=False,
            feedback="Well explained retry bounds.",
            stress_test_prompt="What happens if downstream stalls at 10k req/s?",
        )

        with patch(
            "app.ai.fsm.evaluate_candidate_defense",
            new_callable=AsyncMock,
            return_value=mock_eval_out,
        ) as mock_eval:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                res = await ac.post(
                    f"/api/v1/defense/sessions/{session.session_id}/turn",
                    json={
                        "answer": "Exponential backoff caps retries and applies request timeouts.",
                        "model": "custom/eval-model",
                        "api_key": "eval-secret-key",
                        "base_url": "https://eval.llm.local",
                    },
                    headers=headers,
                )

        assert res.status_code == 200
        assert res.json()["status"] == "stress_test_active"
        mock_eval.assert_awaited_once()
        kwargs = mock_eval.await_args.kwargs
        assert kwargs["model"] == "custom/eval-model"
        assert kwargs["api_key"] == "eval-secret-key"
        assert kwargs["base_url"] == "https://eval.llm.local"
    finally:
        app.dependency_overrides.clear()
        await defense_store.delete(session.session_id)
        async with AsyncSessionLocal() as db_session:
            db_user = await db_session.get(User, user_id)
            if db_user:
                await db_session.delete(db_user)
                await db_session.commit()


@pytest.mark.anyio
async def test_get_defense_session_rejects_non_owner():
    """Verify GET /defense/sessions/{id} rejects non-owners with 404 and allows the owner."""
    owner_id, other_id, project_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    owner_user = User(id=owner_id, email="owner@repodefense.dev")
    other_user = User(id=other_id, email="other@repodefense.dev")
    mock_project = Project(
        id=project_id,
        user_id=owner_id,
        name="owner-repo",
        github_url="https://github.com/test/owner-repo",
    )
    q1 = GroundedQuestion(
        id="q-idor-1",
        category=QuestionCategory.SECURITY,
        question_text="How is session ownership enforced?",
        context_hint="app/api/v1/defense.py",
        cited_evidence_ids=["ev-idor"],
        cited_files=["app/api/v1/defense.py"],
    )
    session = await create_defense_session(str(project_id), [q1], store=defense_store)

    def _mock_db_with(project_result):
        mock_db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = project_result
        mock_db.execute.return_value = res
        return mock_db

    try:
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[get_db] = lambda: _mock_db_with(None)
        other_headers = {"Authorization": f"Bearer {create_test_jwt(other_id, other_user.email)}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            denied = await ac.get(
                f"/api/v1/defense/sessions/{session.session_id}",
                headers=other_headers,
            )
        assert denied.status_code == 404

        app.dependency_overrides[get_current_user] = lambda: owner_user
        app.dependency_overrides[get_db] = lambda: _mock_db_with(mock_project)
        owner_headers = {"Authorization": f"Bearer {create_test_jwt(owner_id, owner_user.email)}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            allowed = await ac.get(
                f"/api/v1/defense/sessions/{session.session_id}",
                headers=owner_headers,
            )
        assert allowed.status_code == 200
        assert allowed.json()["session_id"] == session.session_id
    finally:
        app.dependency_overrides.clear()
        await defense_store.delete(session.session_id)
