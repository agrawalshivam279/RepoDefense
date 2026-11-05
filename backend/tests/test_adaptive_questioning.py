"""Hermetic unit and integration tests for adaptive questioning and topic confidence FSM."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.adaptive import (
    adapt_question_for_difficulty,
    apply_adaptive_session_progression,
    calculate_topic_confidence,
    determine_next_difficulty,
)
from app.ai.fsm import (
    DefenseSessionStore,
    create_defense_session,
    submit_defense_turn,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
    DifficultyLevel,
    EvaluationOutput,
    SecondaryEvaluationOutput,
)
from app.schemas.question import GroundedQuestion, QuestionCategory


def _build_test_question(category: QuestionCategory, title: str) -> GroundedQuestion:
    return GroundedQuestion(
        id=str(uuid.uuid4()),
        category=category,
        question_text=f"How does {title} handle concurrent database writes?",
        context_hint=f"Context for {title}",
        cited_evidence_ids=["ev-1"],
        cited_files=["app/services/db.py"],
    )


def test_calculate_topic_confidence():
    """Verify exponential moving average topic confidence calculations."""
    conf_perfect = calculate_topic_confidence(None, 10)
    assert conf_perfect == 0.80  # 0.6 * 1.0 + 0.4 * 0.5 = 0.8

    conf_low = calculate_topic_confidence(None, 2)
    assert conf_low == 0.32  # 0.6 * 0.2 + 0.4 * 0.5 = 0.32

    conf_followup = calculate_topic_confidence(0.80, 10)
    assert conf_followup == 0.92  # 0.6 * 1.0 + 0.4 * 0.8 = 0.92

    assert calculate_topic_confidence(0.1, 0) == 0.05
    assert calculate_topic_confidence(1.0, 10) == 1.0


def test_determine_next_difficulty():
    """Verify dynamic difficulty adjustment thresholds (< 50% and >= 90%)."""
    # Low score (< 50% / < 5) downgrades
    assert determine_next_difficulty(DifficultyLevel.ADVANCED, 4) == DifficultyLevel.INTERMEDIATE
    assert determine_next_difficulty(DifficultyLevel.INTERMEDIATE, 3) == (
        DifficultyLevel.FOUNDATIONAL
    )
    assert determine_next_difficulty(DifficultyLevel.FOUNDATIONAL, 2) == (
        DifficultyLevel.FOUNDATIONAL
    )

    # High score (>= 90% / >= 9) upgrades
    assert determine_next_difficulty(DifficultyLevel.FOUNDATIONAL, 9) == (
        DifficultyLevel.INTERMEDIATE
    )
    assert determine_next_difficulty(DifficultyLevel.INTERMEDIATE, 10) == DifficultyLevel.ADVANCED
    assert determine_next_difficulty(DifficultyLevel.ADVANCED, 10) == DifficultyLevel.ADVANCED

    # Intermediate scores (5 to 8) retain current tier
    assert determine_next_difficulty(DifficultyLevel.FOUNDATIONAL, 6) == (
        DifficultyLevel.FOUNDATIONAL
    )
    assert determine_next_difficulty(DifficultyLevel.INTERMEDIATE, 7) == (
        DifficultyLevel.INTERMEDIATE
    )
    assert determine_next_difficulty(DifficultyLevel.ADVANCED, 8) == DifficultyLevel.ADVANCED


def test_adapt_question_for_difficulty():
    """Verify question phrasing modulation based on target difficulty level."""
    q = _build_test_question(QuestionCategory.ARCHITECTURE, "CacheLayer")

    # Foundational adaptation
    q_found = adapt_question_for_difficulty(q, DifficultyLevel.FOUNDATIONAL)
    assert q_found.question_text.startswith("[Foundational Drill-Down]")
    assert "core mechanics" in q_found.question_text
    assert q_found.cited_files == q.cited_files

    # Advanced adaptation
    q_adv = adapt_question_for_difficulty(q, DifficultyLevel.ADVANCED)
    assert q_adv.question_text.startswith("[Advanced Production Constraint]")
    assert "10x traffic spike" in q_adv.question_text

    # Intermediate retains original
    q_inter = adapt_question_for_difficulty(q, DifficultyLevel.INTERMEDIATE)
    assert q_inter.question_text == q.question_text


def test_apply_adaptive_session_progression():
    """Verify progression helper updates session topic confidence and next question difficulty."""
    q1 = _build_test_question(QuestionCategory.ARCHITECTURE, "PostgreSQL")
    q2 = _build_test_question(QuestionCategory.SCALABILITY, "Redis")

    session = DefenseSessionState(
        project_id="proj-1",
        status=DefenseStage.QUESTION_ACTIVE,
        current_question_index=0,
        current_difficulty=DifficultyLevel.INTERMEDIATE,
        total_questions=2,
        questions=[
            DefenseQuestionProgress(
                question=q1, difficulty=DifficultyLevel.INTERMEDIATE, final_score=3
            ),
            DefenseQuestionProgress(question=q2, difficulty=DifficultyLevel.INTERMEDIATE),
        ],
    )

    next_diff = apply_adaptive_session_progression(session, completed_index=0)
    assert next_diff == DifficultyLevel.FOUNDATIONAL
    assert session.current_difficulty == DifficultyLevel.FOUNDATIONAL
    assert "architecture" in session.topic_confidence
    assert session.topic_confidence["architecture"] == 0.38  # 0.6 * 0.3 + 0.4 * 0.5 = 0.38

    # Next question adapted
    assert session.questions[1].difficulty == DifficultyLevel.FOUNDATIONAL
    assert session.questions[1].question.question_text.startswith("[Foundational Drill-Down]")


@pytest.mark.anyio
async def test_fsm_adaptive_downgrade_on_struggling_candidate():
    """Verify end-to-end FSM downgrades to foundational when candidate struggles on question 1."""
    store = DefenseSessionStore()
    q1 = _build_test_question(QuestionCategory.SECURITY, "JWTAuth")
    q2 = _build_test_question(QuestionCategory.ARCHITECTURE, "MicroserviceRouter")

    session = await create_defense_session("proj-test-1", [q1, q2], store=store)
    assert session.current_difficulty == DifficultyLevel.INTERMEDIATE

    # Initial defense fails (depth score 3)
    eval_fail = EvaluationOutput(
        passed_initial_defense=False,
        depth_score=3,
        grounding_verified=True,
        feedback="Superficial explanation of JWT verification.",
        mentor_hint="Look into cryptographic signature checking.",
        retest_question="How does HS256 verify signature integrity?",
    )
    with patch("app.ai.fsm.evaluate_candidate_defense", AsyncMock(return_value=eval_fail)):
        session = await submit_defense_turn(session.session_id, "I use JWT for auth.", store=store)
        assert session.status == DefenseStage.MENTOR_ACTIVE

    # Secondary mentor response receives score 4 (final score = 4)
    sec_eval = SecondaryEvaluationOutput(
        handled_successfully=False,
        follow_up_score=4,
        feedback="Still incomplete on HMAC secret hashing.",
    )
    with patch("app.ai.fsm.evaluate_secondary_turn", AsyncMock(return_value=sec_eval)):
        session = await submit_defense_turn(
            session.session_id, "It hashes the payload.", store=store
        )

    # FSM should have advanced to question 2 with FOUNDATIONAL difficulty
    assert session.current_question_index == 1
    assert session.status == DefenseStage.QUESTION_ACTIVE
    assert session.current_difficulty == DifficultyLevel.FOUNDATIONAL
    assert session.questions[1].difficulty == DifficultyLevel.FOUNDATIONAL
    assert session.questions[1].question.question_text.startswith("[Foundational Drill-Down]")
    assert session.topic_confidence["security"] < 0.50


@pytest.mark.anyio
async def test_fsm_adaptive_elevation_on_stellar_candidate():
    """Verify end-to-end FSM elevates to advanced difficulty when candidate scores >= 9."""
    store = DefenseSessionStore()
    q1 = _build_test_question(QuestionCategory.SCALABILITY, "TaskWorker")
    q2 = _build_test_question(QuestionCategory.RELIABILITY, "ConnectionPool")

    session = await create_defense_session("proj-test-2", [q1, q2], store=store)
    assert session.current_difficulty == DifficultyLevel.INTERMEDIATE

    # Initial defense excels (depth score 10)
    eval_pass = EvaluationOutput(
        passed_initial_defense=True,
        depth_score=10,
        grounding_verified=True,
        feedback="Exceptional architectural grasp of async worker queues.",
        stress_test_prompt="What happens if Redis memory exceeds quota during peak load?",
    )
    with patch("app.ai.fsm.evaluate_candidate_defense", AsyncMock(return_value=eval_pass)):
        session = await submit_defense_turn(
            session.session_id, "Detailed async explanation...", store=store
        )
        assert session.status == DefenseStage.STRESS_TEST_ACTIVE

    # Secondary stress test excels (score 10) -> final score 10
    sec_eval = SecondaryEvaluationOutput(
        handled_successfully=True,
        follow_up_score=10,
        feedback="Flawless mitigation strategy using eviction policies and backpressure.",
    )
    with patch("app.ai.fsm.evaluate_secondary_turn", AsyncMock(return_value=sec_eval)):
        session = await submit_defense_turn(
            session.session_id, "We configure allkeys-lru...", store=store
        )

    # FSM should have advanced to question 2 with ADVANCED difficulty
    assert session.current_question_index == 1
    assert session.status == DefenseStage.QUESTION_ACTIVE
    assert session.current_difficulty == DifficultyLevel.ADVANCED
    assert session.questions[1].difficulty == DifficultyLevel.ADVANCED
    assert session.questions[1].question.question_text.startswith(
        "[Advanced Production Constraint]"
    )
    assert session.topic_confidence["scalability"] >= 0.80
