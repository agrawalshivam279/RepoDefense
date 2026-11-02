"""AI module for LiteLLM routing, prompts, and future defense state machines."""

from app.ai.fallbacks import (
    build_deterministic_fallback_questions,
    build_deterministic_fallback_summary,
)
from app.ai.llm import (
    clean_json_response,
    generate_grounded_questions,
    generate_project_summary,
)
from app.ai.prompts import (
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    format_project_summary_user_prompt,
    format_question_generation_user_prompt,
)

__all__ = [
    "PROJECT_SUMMARY_SYSTEM_PROMPT",
    "QUESTION_GENERATION_SYSTEM_PROMPT",
    "build_deterministic_fallback_questions",
    "build_deterministic_fallback_summary",
    "clean_json_response",
    "format_project_summary_user_prompt",
    "format_question_generation_user_prompt",
    "generate_grounded_questions",
    "generate_project_summary",
]
