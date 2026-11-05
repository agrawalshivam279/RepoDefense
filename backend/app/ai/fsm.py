"""Deterministic interview state machine (FSM) governing the RepoDefense core loop."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

import structlog

from app.ai.adaptive import apply_adaptive_session_progression
from app.ai.evaluator import evaluate_candidate_defense, evaluate_secondary_turn
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
    DefenseTurn,
    DifficultyLevel,
    TurnRole,
)
from app.schemas.question import GroundedQuestion

logger = structlog.get_logger(__name__)


class DefenseSessionStore:
    """Thread-safe in-memory storage for active defense sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, DefenseSessionState] = {}
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> Optional[DefenseSessionState]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def save(self, session: DefenseSessionState) -> DefenseSessionState:
        session.updated_at = datetime.now(timezone.utc).isoformat()
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    async def clear(self) -> None:
        async with self._lock:
            self._sessions.clear()


defense_store = DefenseSessionStore()


def _format_question_turn_content(index: int, total: int, question: GroundedQuestion) -> str:
    """Formats the interviewer's presentation of a grounded question."""
    files = ", ".join(question.cited_files) if question.cited_files else "codebase"
    cat_val = (
        question.category.value
        if hasattr(question.category, "value")
        else str(question.category)
    )
    return (
        f"Question {index + 1}/{total} [{cat_val.upper()}]:\n\n"
        f"{question.question_text}\n\nContext: {question.context_hint} (Files: {files})"
    )


async def create_defense_session(
    project_id: str,
    questions: List[GroundedQuestion],
    store: Optional[DefenseSessionStore] = None,
) -> DefenseSessionState:
    """Initializes a new defense session with selected questions and presents question 1."""
    if not questions:
        raise ValueError("Cannot create a defense session with zero questions.")

    target_store = store or defense_store
    q_progress = [
        DefenseQuestionProgress(
            question=q,
            status=DefenseStage.QUESTION_ACTIVE if i == 0 else DefenseStage.INITIALIZING,
            difficulty=DifficultyLevel.INTERMEDIATE,
        )
        for i, q in enumerate(questions)
    ]

    first_q = questions[0]
    cat_val = (
        first_q.category.value
        if hasattr(first_q.category, "value")
        else str(first_q.category)
    )
    initial_turn = DefenseTurn(
        role=TurnRole.INTERVIEWER,
        content=_format_question_turn_content(0, len(questions), first_q),
        stage=DefenseStage.QUESTION_ACTIVE,
        metadata={
            "question_id": first_q.id,
            "category": cat_val,
            "difficulty": DifficultyLevel.INTERMEDIATE.value,
            "cited_files": first_q.cited_files,
        },
    )

    session = DefenseSessionState(
        project_id=project_id,
        status=DefenseStage.QUESTION_ACTIVE,
        current_question_index=0,
        current_difficulty=DifficultyLevel.INTERMEDIATE,
        topic_confidence={},
        total_questions=len(questions),
        questions=q_progress,
        turns=[initial_turn],
    )
    await target_store.save(session)
    logger.info("defense_session_initialized", session_id=session.session_id)
    return session


def _advance_or_complete_session(session: DefenseSessionState) -> None:
    """Advances FSM adaptively to the next question or transitions to SESSION_COMPLETED."""
    completed_idx = session.current_question_index
    apply_adaptive_session_progression(session, completed_idx)

    next_index = completed_idx + 1
    if next_index < session.total_questions:
        session.current_question_index = next_index
        next_prog = session.questions[next_index]
        next_prog.status = DefenseStage.QUESTION_ACTIVE
        session.status = DefenseStage.QUESTION_ACTIVE

        turn_content = _format_question_turn_content(
            next_index, session.total_questions, next_prog.question
        )
        cat_val = (
            next_prog.question.category.value
            if hasattr(next_prog.question.category, "value")
            else str(next_prog.question.category)
        )
        session.turns.append(
            DefenseTurn(
                role=TurnRole.INTERVIEWER,
                content=turn_content,
                stage=DefenseStage.QUESTION_ACTIVE,
                metadata={
                    "question_id": next_prog.question.id,
                    "category": cat_val,
                    "difficulty": next_prog.difficulty.value,
                    "cited_files": next_prog.question.cited_files,
                },
            )
        )
    else:
        session.status = DefenseStage.SESSION_COMPLETED
        scores = [q.final_score for q in session.questions if q.final_score is not None]
        session.overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        msg = f"Defense session concluded. Candidate overall score: {session.overall_score}/10."
        session.turns.append(
            DefenseTurn(
                role=TurnRole.SYSTEM,
                content=msg,
                stage=DefenseStage.SESSION_COMPLETED,
                metadata={
                    "overall_score": session.overall_score,
                    "topic_confidence": session.topic_confidence,
                },
            )
        )


async def _process_secondary_turn(
    session: DefenseSessionState,
    prog: DefenseQuestionProgress,
    answer: str,
    prompt_context: str,
    is_stress: bool,
) -> None:
    """Helper to process stress test or mentor secondary turns without code duplication."""
    secondary_out = await evaluate_secondary_turn(prompt_context, answer)
    initial = prog.defense_score or (5 if is_stress else 3)
    w_init, w_sec = (0.6, 0.4) if is_stress else (0.4, 0.6)
    prog.final_score = int(round(w_init * initial + w_sec * secondary_out.follow_up_score))
    prog.status = DefenseStage.QUESTION_COMPLETED

    if is_stress:
        prog.stress_test_response = answer
        label = "Evaluation"
    else:
        prog.retest_response = answer
        label = "Mentor Evaluation"

    session.turns.append(
        DefenseTurn(
            role=TurnRole.INTERVIEWER,
            content=f"{label}: {secondary_out.feedback}",
            stage=DefenseStage.QUESTION_COMPLETED,
            metadata={"final_score": prog.final_score, "difficulty": prog.difficulty.value},
        )
    )
    _advance_or_complete_session(session)


async def submit_defense_turn(
    session_id: str,
    candidate_answer: str,
    store: Optional[DefenseSessionStore] = None,
) -> DefenseSessionState:
    """Executes a single turn of the defense state machine for a candidate's answer."""
    target_store = store or defense_store
    session = await target_store.get(session_id)
    if not session:
        raise KeyError(f"Defense session '{session_id}' not found.")
    if session.status == DefenseStage.SESSION_COMPLETED:
        raise ValueError("Cannot submit an answer to an already completed defense session.")

    prog = session.questions[session.current_question_index]

    if session.status == DefenseStage.QUESTION_ACTIVE:
        session.turns.append(
            DefenseTurn(
                role=TurnRole.CANDIDATE,
                content=candidate_answer,
                stage=DefenseStage.QUESTION_ACTIVE,
            )
        )
        eval_out = await evaluate_candidate_defense(prog.question, candidate_answer)
        prog.initial_defense = candidate_answer
        prog.defense_score = eval_out.depth_score
        prog.feedback = eval_out.feedback

        if eval_out.passed_initial_defense:
            prog.status = DefenseStage.STRESS_TEST_ACTIVE
            session.status = DefenseStage.STRESS_TEST_ACTIVE
            prog.stress_test_prompt = eval_out.stress_test_prompt
            content = (
                f"{eval_out.feedback}\n\nProduction Stress-Test:\n"
                f"{eval_out.stress_test_prompt}"
            )
            stage = DefenseStage.STRESS_TEST_ACTIVE
        else:
            prog.status = DefenseStage.MENTOR_ACTIVE
            session.status = DefenseStage.MENTOR_ACTIVE
            prog.mentor_hint = eval_out.mentor_hint
            prog.retest_question = eval_out.retest_question
            content = (
                f"{eval_out.feedback}\n\nMentor Hint: {eval_out.mentor_hint}\n\n"
                f"Follow-up: {eval_out.retest_question}"
            )
            stage = DefenseStage.MENTOR_ACTIVE

        session.turns.append(
            DefenseTurn(
                role=TurnRole.INTERVIEWER,
                content=content,
                stage=stage,
                metadata={
                    "depth_score": eval_out.depth_score,
                    "grounding_verified": eval_out.grounding_verified,
                },
            )
        )

    elif session.status == DefenseStage.STRESS_TEST_ACTIVE:
        session.turns.append(
            DefenseTurn(
                role=TurnRole.CANDIDATE,
                content=candidate_answer,
                stage=DefenseStage.STRESS_TEST_ACTIVE,
            )
        )
        prompt_ctx = prog.stress_test_prompt or prog.question.question_text
        await _process_secondary_turn(session, prog, candidate_answer, prompt_ctx, is_stress=True)

    elif session.status == DefenseStage.MENTOR_ACTIVE:
        session.turns.append(
            DefenseTurn(
                role=TurnRole.CANDIDATE,
                content=candidate_answer,
                stage=DefenseStage.MENTOR_ACTIVE,
            )
        )
        prompt_ctx = prog.retest_question or prog.question.question_text
        await _process_secondary_turn(session, prog, candidate_answer, prompt_ctx, is_stress=False)

    else:
        raise ValueError(f"Cannot submit candidate turn in state '{session.status}'.")

    await target_store.save(session)
    return session
