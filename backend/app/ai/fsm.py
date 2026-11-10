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
    EvaluationOutput,
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

    async def get_by_project(self, project_id: str) -> List[DefenseSessionState]:
        async with self._lock:
            return [s for s in self._sessions.values() if s.project_id == project_id]

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
    cat_val = getattr(question.category, "value", str(question.category))
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
    cat_val = getattr(first_q.category, "value", str(first_q.category))
    session = DefenseSessionState(
        project_id=project_id,
        status=DefenseStage.QUESTION_ACTIVE,
        current_question_index=0,
        current_difficulty=DifficultyLevel.INTERMEDIATE,
        topic_confidence={},
        total_questions=len(questions),
        questions=q_progress,
        turns=[
            DefenseTurn(
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
        ],
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
        next_prog.status = session.status = DefenseStage.QUESTION_ACTIVE
        cat_val = getattr(next_prog.question.category, "value", str(next_prog.question.category))
        session.turns.append(
            DefenseTurn(
                role=TurnRole.INTERVIEWER,
                content=_format_question_turn_content(
                    next_index, session.total_questions, next_prog.question
                ),
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


def _branch_to_stress_or_mentor(
    session: DefenseSessionState,
    prog: DefenseQuestionProgress,
    eval_out: EvaluationOutput,
) -> None:
    """Branches question state to STRESS_TEST_ACTIVE or MENTOR_ACTIVE based on evaluation."""
    if eval_out.passed_initial_defense:
        prog.status = session.status = DefenseStage.STRESS_TEST_ACTIVE
        prog.stress_test_prompt = eval_out.stress_test_prompt
        content = f"{eval_out.feedback}\n\nProduction Stress-Test:\n{eval_out.stress_test_prompt}"
    else:
        ref_file = prog.question.cited_files[0] if prog.question.cited_files else "the module"
        prog.status = session.status = DefenseStage.MENTOR_ACTIVE
        prog.mentor_hint = eval_out.mentor_hint or (
            f"Review how `{ref_file}` coordinates resource lifecycle and boundaries. "
            "Think about failure modes, connection limits, and defensive checks."
        )
        prog.retest_question = eval_out.retest_question or (
            f"In `{ref_file}`, what specific boundary or fallback pattern would you implement "
            "to ensure graceful degradation under failure?"
        )
        content = (
            f"{eval_out.feedback}\n\nMentor Hint: {prog.mentor_hint}\n\n"
            f"Follow-up: {prog.retest_question}"
        )

    session.turns.append(
        DefenseTurn(
            role=TurnRole.INTERVIEWER,
            content=content,
            stage=session.status,
            metadata={
                "depth_score": eval_out.depth_score,
                "grounding_verified": eval_out.grounding_verified,
            },
        )
    )


async def submit_defense_turn(
    session_id: str,
    candidate_answer: str = "",
    store: Optional[DefenseSessionStore] = None,
    user_response: Optional[str] = None,
) -> DefenseSessionState:
    """Executes a single turn of the defense state machine for a candidate's answer."""
    candidate_answer = candidate_answer or user_response or ""
    target_store = store or defense_store
    session = await target_store.get(session_id)
    if not session:
        raise KeyError(f"Defense session '{session_id}' not found.")
    if session.status == DefenseStage.SESSION_COMPLETED:
        raise ValueError("Cannot submit an answer to an already completed defense session.")

    prog = session.questions[session.current_question_index]
    session.turns.append(
        DefenseTurn(role=TurnRole.CANDIDATE, content=candidate_answer, stage=session.status)
    )

    if session.status == DefenseStage.QUESTION_ACTIVE:
        eval_out = await evaluate_candidate_defense(prog.question, candidate_answer)
        prog.initial_defense = candidate_answer
        prog.defense_score = eval_out.depth_score
        prog.feedback = eval_out.feedback

        if eval_out.is_vague and prog.pushback_count < 1:
            prog.pushback_count += 1
            prog.pushback_prompt = (
                eval_out.pushback_prompt
                or "Your answer is too high-level. What specific code mechanisms govern this?"
            )
            prog.status = session.status = DefenseStage.PUSHBACK_ACTIVE
            pb_content = (
                f"{eval_out.feedback}\n\nPrincipal Engineer Pushback:\n{prog.pushback_prompt}"
            )
            session.turns.append(
                DefenseTurn(
                    role=TurnRole.INTERVIEWER,
                    content=pb_content,
                    stage=DefenseStage.PUSHBACK_ACTIVE,
                    metadata={"depth_score": eval_out.depth_score, "is_vague": True},
                )
            )
        else:
            _branch_to_stress_or_mentor(session, prog, eval_out)

    elif session.status == DefenseStage.PUSHBACK_ACTIVE:
        prog.pushback_response = candidate_answer
        eval_out = await evaluate_candidate_defense(prog.question, candidate_answer)
        prog.defense_score = eval_out.depth_score
        prog.feedback = eval_out.feedback
        _branch_to_stress_or_mentor(session, prog, eval_out)

    elif session.status == DefenseStage.STRESS_TEST_ACTIVE:
        prompt_ctx = prog.stress_test_prompt or prog.question.question_text
        await _process_secondary_turn(session, prog, candidate_answer, prompt_ctx, is_stress=True)

    elif session.status == DefenseStage.MENTOR_ACTIVE:
        prompt_ctx = prog.retest_question or prog.question.question_text
        await _process_secondary_turn(session, prog, candidate_answer, prompt_ctx, is_stress=False)

    else:
        raise ValueError(f"Cannot submit candidate turn in state '{session.status}'.")

    await target_store.save(session)
    return session
