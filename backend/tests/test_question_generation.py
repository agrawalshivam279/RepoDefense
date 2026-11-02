"""Unit and integration tests for evidence-grounded question generation."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.fallbacks import build_deterministic_fallback_questions
from app.ai.llm import generate_grounded_questions
from app.ai.prompts import format_question_generation_user_prompt
from app.schemas.question import (
    EvidenceRef,
    GroundedQuestion,
    QuestionCategory,
    QuestionGenerationInput,
    QuestionGenerationResponse,
)


def test_question_schemas_and_serialization():
    """Verify question schema integrity and category enum serialization."""
    q = GroundedQuestion(
        id=str(uuid.uuid4()),
        category=QuestionCategory.SCALABILITY,
        question_text="How does your Redis queue handle task deduplication?",
        context_hint="Referencing worker cloner in app/workers/cloner.py",
        cited_evidence_ids=["ev-123"],
        cited_files=["app/workers/cloner.py"],
    )

    dumped = q.model_dump()
    assert dumped["category"] == "scalability"
    assert "ev-123" in dumped["cited_evidence_ids"]
    assert "app/workers/cloner.py" in dumped["cited_files"]


def test_prompt_formatting_and_evidence_xml():
    """Verify XML context isolation and escaping for question generation prompts."""
    ev = EvidenceRef(
        id="ev-999",
        evidence_type="database",
        title="PostgreSQL 17 <pgvector>",
        description="Async SQLAlchemy database connection pool",
        file_path="app/core/database.py",
        start_line=10,
        end_line=45,
    )
    gen_input = QuestionGenerationInput(
        project_name="RepoDefense <test>",
        summary_narrative="Modular monolith with FastAPI",
        architectural_style="Modular Monolith",
        evidence_items=[ev],
        requested_count=3,
    )

    prompt = format_question_generation_user_prompt(gen_input)
    assert "<repository_context>" in prompt
    assert "<project_name>RepoDefense &lt;test&gt;</project_name>" in prompt
    assert "<evidence_catalog>" in prompt
    assert '<evidence_item id="ev-999">' in prompt
    assert "<title>PostgreSQL 17 &lt;pgvector&gt;</title>" in prompt
    assert "<lines>10-45</lines>" in prompt


def test_build_deterministic_fallback_questions():
    """Verify categorized fallback generation directly from evidence records."""
    db_ev = EvidenceRef(
        id="ev-1",
        evidence_type="database",
        title="Supabase PostgreSQL",
        description="Core database connection pool",
        file_path="app/core/database.py",
        start_line=15,
        end_line=40,
    )
    auth_ev = EvidenceRef(
        id="ev-2",
        evidence_type="auth",
        title="Supabase JWT Verification",
        description="Stateless token validation middleware",
        file_path="app/core/security.py",
        start_line=20,
        end_line=60,
    )
    gen_input = QuestionGenerationInput(
        project_name="RepoDefense",
        evidence_items=[db_ev, auth_ev],
        requested_count=2,
    )

    questions = build_deterministic_fallback_questions(gen_input)
    assert len(questions) == 2
    assert any(q.category == QuestionCategory.SCALABILITY for q in questions)
    assert any(q.category == QuestionCategory.SECURITY for q in questions)
    assert "app/core/database.py" in questions[0].cited_files
    assert "ev-1" in questions[0].cited_evidence_ids


def test_fallback_questions_empty_evidence():
    """Verify safe fallback question synthesis when project has zero evidence records."""
    gen_input = QuestionGenerationInput(
        project_name="EmptyRepo",
        evidence_items=[],
        requested_count=1,
    )
    questions = build_deterministic_fallback_questions(gen_input)
    assert len(questions) == 1
    assert questions[0].category == QuestionCategory.ARCHITECTURE
    assert "EmptyRepo" in questions[0].question_text


@pytest.mark.anyio
async def test_generate_grounded_questions_empty_key_fallback():
    """Verify immediate deterministic fallback when API key is empty."""
    ev = EvidenceRef(
        id="ev-10",
        evidence_type="queue",
        title="ARQ Redis Pool",
        description="Background job queue",
        file_path="app/core/redis.py",
        start_line=1,
        end_line=25,
    )
    gen_input = QuestionGenerationInput(
        project_name="QueueProject",
        evidence_items=[ev],
        requested_count=1,
    )

    questions = await generate_grounded_questions(gen_input, api_key="")
    assert len(questions) == 1
    assert questions[0].category == QuestionCategory.RELIABILITY
    assert "app/core/redis.py" in questions[0].cited_files


@pytest.mark.anyio
async def test_generate_grounded_questions_mock_llm_success():
    """Verify structured parsing of question array from mocked LiteLLM completion."""
    ev = EvidenceRef(
        id="ev-fastapi",
        evidence_type="framework",
        title="FastAPI Web Framework",
        description="REST routing layer",
        file_path="app/main.py",
        start_line=1,
        end_line=50,
    )
    gen_input = QuestionGenerationInput(
        project_name="FastAPIApp",
        evidence_items=[ev],
        requested_count=2,
    )

    mock_llm_json = """[
      {
        "category": "architecture",
        "question_text": "Why did you select FastAPI over Flask or Django for this service?",
        "context_hint": "In app/main.py, FastAPI application is configured with CORS middleware",
        "cited_evidence_ids": ["ev-fastapi"],
        "cited_files": ["app/main.py"]
      },
      {
        "category": "scalability",
        "question_text": "How do your async endpoints handle blocking I/O calls during peak load?",
        "context_hint": "Referring to asynchronous request handlers in app/main.py",
        "cited_evidence_ids": ["ev-fastapi"],
        "cited_files": ["app/main.py"]
      }
    ]"""

    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = mock_llm_json
    mock_response.choices = [mock_choice]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        questions = await generate_grounded_questions(
            gen_input,
            api_key="mock-key",
            base_url="http://127.0.0.1:31415/v1",
        )

        assert mock_acompletion.await_count == 1
        assert len(questions) == 2
        assert questions[0].category == QuestionCategory.ARCHITECTURE
        assert questions[1].category == QuestionCategory.SCALABILITY
        assert "ev-fastapi" in questions[0].cited_evidence_ids


@pytest.mark.anyio
async def test_generate_grounded_questions_retry_on_failure():
    """Verify exponential backoff retry when first LLM attempt raises an exception."""
    gen_input = QuestionGenerationInput(project_name="RetryProject", requested_count=1)

    mock_llm_json = """[
      {
        "category": "reliability",
        "question_text": "What happens if a transient network partition interrupts Redis?",
        "context_hint": "Redis queue configuration",
        "cited_evidence_ids": [],
        "cited_files": ["app/core/redis.py"]
      }
    ]"""

    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = mock_llm_json
    mock_response.choices = [mock_choice]

    with (
        patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_acompletion.side_effect = [RuntimeError("Provider 500 error"), mock_response]

        questions = await generate_grounded_questions(
            gen_input,
            api_key="mock-key",
            max_retries=2,
            timeout_seconds=5.0,
        )

        assert mock_acompletion.await_count == 2
        assert mock_sleep.await_count == 1
        assert len(questions) == 1
        assert questions[0].category == QuestionCategory.RELIABILITY


@pytest.mark.anyio
async def test_generate_grounded_questions_malformed_json_fallback():
    """Verify fallback questions when LLM returns non-JSON or conversational text."""
    ev = EvidenceRef(
        id="ev-sec",
        evidence_type="auth",
        title="JWT Security",
        description="Auth token handler",
        file_path="app/core/security.py",
        start_line=1,
        end_line=30,
    )
    gen_input = QuestionGenerationInput(
        project_name="MalformedApp",
        evidence_items=[ev],
        requested_count=1,
    )

    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = "Here are some nice questions about your code!"
    mock_response.choices = [mock_choice]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        questions = await generate_grounded_questions(
            gen_input,
            api_key="mock-key",
            max_retries=0,
            timeout_seconds=5.0,
        )

        assert mock_acompletion.await_count == 1
        assert len(questions) == 1
        assert questions[0].category == QuestionCategory.SECURITY
        assert "app/core/security.py" in questions[0].cited_files


def test_question_generation_response_contract():
    """Verify QuestionGenerationResponse aggregation metrics."""
    q1 = GroundedQuestion(
        category=QuestionCategory.SCALABILITY,
        question_text="Q1",
        context_hint="Hint1",
        cited_evidence_ids=["ev-1"],
        cited_files=["file1.py"],
    )
    q2 = GroundedQuestion(
        category=QuestionCategory.SECURITY,
        question_text="Q2",
        context_hint="Hint2",
        cited_evidence_ids=["ev-1", "ev-2"],
        cited_files=["file2.py"],
    )

    resp = QuestionGenerationResponse(
        project_id=uuid.uuid4(),
        project_name="MetricsProject",
        questions=[q1, q2],
        total_generated=2,
        grounded_evidence_count=2,
    )

    assert resp.total_generated == 2
    assert resp.grounded_evidence_count == 2
