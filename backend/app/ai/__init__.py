"""AI module for LiteLLM routing, prompts, and defense state machine."""

from app.ai.adaptive import (
    adapt_question_for_difficulty,
    apply_adaptive_session_progression,
    calculate_topic_confidence,
    determine_next_difficulty,
)
from app.ai.claim_extractor import (
    extract_technical_claims,
    extract_text_from_pdf,
)
from app.ai.claim_verifier import (
    verify_claims_batch,
    verify_single_claim,
)
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
    CLAIM_EXTRACTION_SYSTEM_PROMPT,
    CLAIM_VERIFICATION_SYSTEM_PROMPT,
    DEFENSE_EVALUATION_SYSTEM_PROMPT,
    DEFENSE_REPORT_SYSTEM_PROMPT,
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    SECONDARY_EVALUATION_SYSTEM_PROMPT,
    format_claim_extraction_user_prompt,
    format_claim_verification_user_prompt,
    format_defense_evaluation_user_prompt,
    format_defense_report_user_prompt,
    format_project_summary_user_prompt,
    format_question_generation_user_prompt,
    format_secondary_evaluation_user_prompt,
)
from app.ai.report_generator import (
    aggregate_category_scores,
    build_deterministic_fallback_report,
    generate_defense_report,
)

__all__ = [
    "CLAIM_EXTRACTION_SYSTEM_PROMPT",
    "CLAIM_VERIFICATION_SYSTEM_PROMPT",
    "DEFENSE_EVALUATION_SYSTEM_PROMPT",
    "DEFENSE_REPORT_SYSTEM_PROMPT",
    "DefenseSessionStore",
    "PROJECT_SUMMARY_SYSTEM_PROMPT",
    "QUESTION_GENERATION_SYSTEM_PROMPT",
    "SECONDARY_EVALUATION_SYSTEM_PROMPT",
    "adapt_question_for_difficulty",
    "aggregate_category_scores",
    "apply_adaptive_session_progression",
    "build_deterministic_fallback_evaluation",
    "build_deterministic_fallback_questions",
    "build_deterministic_fallback_report",
    "build_deterministic_fallback_secondary",
    "build_deterministic_fallback_summary",
    "calculate_topic_confidence",
    "clean_json_response",
    "create_defense_session",
    "defense_store",
    "determine_next_difficulty",
    "evaluate_candidate_defense",
    "evaluate_secondary_turn",
    "extract_technical_claims",
    "extract_text_from_pdf",
    "format_claim_extraction_user_prompt",
    "format_claim_verification_user_prompt",
    "format_defense_evaluation_user_prompt",
    "format_defense_report_user_prompt",
    "format_project_summary_user_prompt",
    "format_question_generation_user_prompt",
    "format_secondary_evaluation_user_prompt",
    "generate_defense_report",
    "generate_grounded_questions",
    "generate_project_summary",
    "submit_defense_turn",
    "verify_claims_batch",
    "verify_single_claim",
]
