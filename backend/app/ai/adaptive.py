"""Adaptive questioning engine and dynamic difficulty adjustment for defense sessions."""

from typing import Optional

import structlog

from app.schemas.defense import DefenseSessionState, DifficultyLevel
from app.schemas.question import GroundedQuestion

logger = structlog.get_logger(__name__)


def calculate_topic_confidence(
    prior: Optional[float],
    score: int,
    alpha: float = 0.6,
) -> float:
    """Calculates updated exponential moving average confidence (0.0 to 1.0) for a topic."""
    norm_score = max(0.0, min(1.0, score / 10.0))
    prior_conf = 0.5 if prior is None or prior <= 0.0 else max(0.0, min(1.0, prior))
    updated = round(alpha * norm_score + (1.0 - alpha) * prior_conf, 2)
    return max(0.05, min(1.0, updated))


def determine_next_difficulty(
    current: DifficultyLevel,
    score: int,
) -> DifficultyLevel:
    """Adjusts difficulty: < 50% (< 5) downgrades, >= 90% (>= 9) upgrades, else holds."""
    if score < 5:
        if current == DifficultyLevel.ADVANCED:
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.FOUNDATIONAL
    elif score >= 9:
        if current == DifficultyLevel.FOUNDATIONAL:
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.ADVANCED
    return current


def adapt_question_for_difficulty(
    question: GroundedQuestion,
    target_difficulty: DifficultyLevel,
    focus_topic: Optional[str] = None,
) -> GroundedQuestion:
    """Adapts question phrasing and scope to match target difficulty and drill-down topic."""
    orig_text = question.question_text
    # Remove existing difficulty tag prefixes if re-adapting
    for prefix in ["[Foundational Drill-Down] ", "[Advanced Production Constraint] "]:
        if orig_text.startswith(prefix):
            orig_text = orig_text[len(prefix):]

    if target_difficulty == DifficultyLevel.FOUNDATIONAL:
        adapted_text = (
            f"[Foundational Drill-Down] {orig_text} "
            f"Specifically break down the core mechanics and rationale step by step."
        )
    elif target_difficulty == DifficultyLevel.ADVANCED:
        adapted_text = (
            f"[Advanced Production Constraint] {orig_text} "
            f"Under a 10x traffic spike or network partition, how does this design hold up?"
        )
    else:
        adapted_text = orig_text

    return GroundedQuestion(
        id=question.id,
        category=question.category,
        question_text=adapted_text,
        context_hint=question.context_hint,
        cited_evidence_ids=question.cited_evidence_ids,
        cited_files=question.cited_files,
    )


def apply_adaptive_session_progression(
    session: DefenseSessionState,
    completed_index: int,
) -> DifficultyLevel:
    """Updates topic confidence, determines next difficulty, and adapts upcoming questions."""
    prog = session.questions[completed_index]
    cat_key = (
        prog.question.category.value
        if hasattr(prog.question.category, "value")
        else str(prog.question.category)
    )
    score = prog.final_score if prog.final_score is not None else (prog.defense_score or 5)

    prior_conf = session.topic_confidence.get(cat_key, 0.5)
    new_conf = calculate_topic_confidence(prior_conf, score)
    session.topic_confidence[cat_key] = new_conf

    next_diff = determine_next_difficulty(session.current_difficulty, score)
    session.current_difficulty = next_diff

    logger.info(
        "adaptive_progression_applied",
        session_id=session.session_id,
        topic=cat_key,
        score=score,
        topic_confidence=new_conf,
        next_difficulty=next_diff.value,
    )

    next_index = completed_index + 1
    if next_index < session.total_questions:
        next_prog = session.questions[next_index]
        drill_topic = cat_key if score < 5 else None
        next_prog.question = adapt_question_for_difficulty(
            next_prog.question, next_diff, focus_topic=drill_topic
        )
        next_prog.difficulty = next_diff

    return next_diff
