"""AI module for LiteLLM routing, prompts, and future defense state machines."""

from app.ai.llm import (
    build_deterministic_fallback_summary,
    clean_json_response,
    generate_project_summary,
)
from app.ai.prompts import (
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    format_project_summary_user_prompt,
)

__all__ = [
    "PROJECT_SUMMARY_SYSTEM_PROMPT",
    "build_deterministic_fallback_summary",
    "clean_json_response",
    "format_project_summary_user_prompt",
    "generate_project_summary",
]
