"""Unit and integration tests for AI Pushback Logic & Multi-Turn Clarification Engine."""

import pytest

from app.ai.fallbacks import build_deterministic_fallback_evaluation
from app.ai.fsm import (
    DefenseSessionStore,
    create_defense_session,
    submit_defense_turn,
)
from app.core.config import settings
from app.schemas.defense import DefenseStage, TurnRole
from app.schemas.question import GroundedQuestion, QuestionCategory


@pytest.fixture(autouse=True)
def default_offline_evaluator(monkeypatch):
    """Ensure fast, hermetic tests by disabling remote LLM calls by default."""
    monkeypatch.setattr(settings, "FREELLMAPI_API_KEY", "")


def _sample_question(index: int = 1) -> GroundedQuestion:
    return GroundedQuestion(
        id=f"q-pushback-{index}",
        category=QuestionCategory.ARCHITECTURE,
        question_text=f"How do you enforce idempotency in transaction handler {index}?",
        context_hint=f"Context for transaction handler {index}",
        cited_evidence_ids=[f"ev-pb-{index}"],
        cited_files=[f"app/services/tx_{index}.py"],
    )


def test_deterministic_fallback_vague_detection():
    """Verify fallback evaluator correctly classifies vague, failing, and strong answers."""
    q = _sample_question(1)

    # Vague answer containing buzzwords without implementation details
    vague_ans = "We followed standard practice and best practice so it just works fine."
    vague_out = build_deterministic_fallback_evaluation(q, vague_ans)
    assert vague_out.is_vague is True
    assert not vague_out.passed_initial_defense
    assert vague_out.depth_score == 4
    assert vague_out.pushback_prompt is not None
    assert "tx_1.py" in vague_out.pushback_prompt
    assert vague_out.stress_test_prompt is None
    assert vague_out.mentor_hint is None

    # Explicit failure (not vague, admits ignorance) -> branches directly to mentor
    fail_ans = "I don't know, copied from tutorial and not sure about it."
    fail_out = build_deterministic_fallback_evaluation(q, fail_ans)
    assert fail_out.is_vague is False
    assert not fail_out.passed_initial_defense
    assert fail_out.mentor_hint is not None
    assert fail_out.pushback_prompt is None

    # Strong answer with technical keywords and depth
    strong_ans = (
        "We implement unique idempotency keys in Redis with atomic SETNX locks "
        "and transactional rollback blocks to prevent duplicate executions."
    )
    strong_out = build_deterministic_fallback_evaluation(q, strong_ans)
    assert strong_out.is_vague is False
    assert strong_out.passed_initial_defense is True
    assert strong_out.depth_score >= 6
    assert strong_out.stress_test_prompt is not None
    assert strong_out.pushback_prompt is None


@pytest.mark.anyio
async def test_fsm_pushback_transition_on_vague_answer():
    """Verify vague answer triggers PUSHBACK_ACTIVE state and records pushback prompt."""
    store = DefenseSessionStore()
    q = _sample_question(1)
    session = await create_defense_session("proj-pb-1", [q], store=store)

    vague_ans = "It's standard practice in Python web frameworks to do this."
    session = await submit_defense_turn(session.session_id, vague_ans, store=store)

    assert session.status == DefenseStage.PUSHBACK_ACTIVE
    prog = session.questions[0]
    assert prog.status == DefenseStage.PUSHBACK_ACTIVE
    assert prog.pushback_count == 1
    assert prog.pushback_prompt is not None
    assert "tx_1.py" in prog.pushback_prompt

    # Turns: 0 = Question, 1 = Candidate initial vague answer, 2 = Pushback prompt
    assert len(session.turns) == 3
    assert session.turns[1].role == TurnRole.CANDIDATE
    assert session.turns[1].content == vague_ans
    assert session.turns[2].role == TurnRole.INTERVIEWER
    assert session.turns[2].stage == DefenseStage.PUSHBACK_ACTIVE
    assert session.turns[2].metadata.get("is_vague") is True


@pytest.mark.anyio
async def test_fsm_pushback_clarification_advances_to_stress_test():
    """Verify strong clarification in PUSHBACK_ACTIVE advances to STRESS_TEST_ACTIVE."""
    store = DefenseSessionStore()
    q = _sample_question(1)
    session = await create_defense_session("proj-pb-2", [q], store=store)

    vague_ans = "We used the normal way of handling transactions across our services."
    session = await submit_defense_turn(session.session_id, vague_ans, store=store)
    assert session.status == DefenseStage.PUSHBACK_ACTIVE

    # Provide strong technical clarification
    clarification = (
        "Specifically, we persist an idempotency token with distributed redis locks, "
        "and if a duplicate key arrives, we return the cached response with retry queues."
    )
    session = await submit_defense_turn(session.session_id, clarification, store=store)

    assert session.status == DefenseStage.STRESS_TEST_ACTIVE
    prog = session.questions[0]
    assert prog.status == DefenseStage.STRESS_TEST_ACTIVE
    assert prog.pushback_response == clarification
    assert prog.stress_test_prompt is not None

    # Turns: 0=Q, 1=Candidate vague, 2=Pushback, 3=Candidate clarification, 4=Stress prompt
    assert len(session.turns) == 5
    assert session.turns[3].role == TurnRole.CANDIDATE
    assert session.turns[3].stage == DefenseStage.PUSHBACK_ACTIVE
    assert session.turns[4].role == TurnRole.INTERVIEWER
    assert session.turns[4].stage == DefenseStage.STRESS_TEST_ACTIVE


@pytest.mark.anyio
async def test_fsm_pushback_clarification_fails_to_mentor():
    """Verify weak clarification in PUSHBACK_ACTIVE branches to MENTOR_ACTIVE."""
    store = DefenseSessionStore()
    q = _sample_question(1)
    session = await create_defense_session("proj-pb-3", [q], store=store)

    vague_ans = "It just works without issues in our normal flow."
    session = await submit_defense_turn(session.session_id, vague_ans, store=store)
    assert session.status == DefenseStage.PUSHBACK_ACTIVE

    # Fails clarification by admitting lack of knowledge
    weak_clarification = "I don't know the exact details, I wasn't the author of that."
    session = await submit_defense_turn(session.session_id, weak_clarification, store=store)

    assert session.status == DefenseStage.MENTOR_ACTIVE
    prog = session.questions[0]
    assert prog.status == DefenseStage.MENTOR_ACTIVE
    assert prog.pushback_response == weak_clarification
    assert prog.mentor_hint is not None
    assert prog.retest_question is not None

    assert len(session.turns) == 5
    assert session.turns[4].role == TurnRole.INTERVIEWER
    assert session.turns[4].stage == DefenseStage.MENTOR_ACTIVE


@pytest.mark.anyio
async def test_fsm_pushback_limit_prevents_infinite_loop():
    """Verify that a second vague clarification transitions to MENTOR_ACTIVE without looping."""
    store = DefenseSessionStore()
    q = _sample_question(1)
    session = await create_defense_session("proj-pb-4", [q], store=store)

    vague_ans = "We adhered to best practice patterns throughout the module."
    session = await submit_defense_turn(session.session_id, vague_ans, store=store)
    assert session.status == DefenseStage.PUSHBACK_ACTIVE
    assert session.questions[0].pushback_count == 1

    # Second vague answer during clarification must not trigger a second pushback
    second_vague = "Like I said, it is just boilerplate and standard practice."
    session = await submit_defense_turn(session.session_id, second_vague, store=store)

    # Fails to mentor instead of re-entering pushback
    assert session.status == DefenseStage.MENTOR_ACTIVE
    prog = session.questions[0]
    assert prog.status == DefenseStage.MENTOR_ACTIVE
    assert prog.pushback_count == 1
    assert prog.mentor_hint is not None
