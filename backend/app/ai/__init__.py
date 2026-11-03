"""AI module for LiteLLM routing, prompts, and defense state machine."""

from app.ai.evaluator import (
    evaluate_candidate_defense,
    evaluate_secondary_turn,
)
from app.ai.fallbacks import (
    build_deterministic_fallback_evaluation,
    build_deterministic_fallback_questions,
    build_deterministic_fallback_secondary,
    build_deterministic_fallback_summary,
)
from app.ai.fsm import (
    DefenseSessionStore,
    create_defense_session,
    defense_store,
    submit_defense_turn,
)
from app.ai.llm import (
    clean_json_response,
    generate_grounded_questions,
    generate_project_summary,
)
from app.ai.prompts import (
    DEFENSE_EVALUATION_SYSTEM_PROMPT,
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    SECONDARY_EVALUATION_SYSTEM_PROMPT,
    format_defense_evaluation_user_prompt,
    format_project_summary_user_prompt,
    format_question_generation_user_prompt,
    format_secondary_evaluation_user_prompt,
)

__all__ = [
    "DEFENSE_EVALUATION_SYSTEM_PROMPT",
    "DefenseSessionStore",
    "PROJECT_SUMMARY_SYSTEM_PROMPT",
    "QUESTION_GENERATION_SYSTEM_PROMPT",
    "SECONDARY_EVALUATION_SYSTEM_PROMPT",
    "build_deterministic_fallback_evaluation",
    "build_deterministic_fallback_questions",
    "build_deterministic_fallback_secondary",
    "build_deterministic_fallback_summary",
    "clean_json_response",
    "create_defense_session",
    "defense_store",
    "evaluate_candidate_defense",
    "evaluate_secondary_turn",
    "format_defense_evaluation_user_prompt",
    "format_project_summary_user_prompt",
    "format_question_generation_user_prompt",
    "format_secondary_evaluation_user_prompt",
    "generate_grounded_questions",
    "generate_project_summary",
    "submit_defense_turn",
]
