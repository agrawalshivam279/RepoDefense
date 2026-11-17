"""AI generator and evaluator for Targeted Re-Testing."""

import asyncio
import json
import os
from typing import Any, Dict, Optional, Tuple

import structlog

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.retest_fallbacks import (  # noqa: E402
    evaluate_retest_fallback,
    get_fallback_retest_question,
)
from app.ai.retest_prompts import (  # noqa: E402
    RETEST_EVALUATION_SYSTEM_PROMPT,
    RETEST_SYSTEM_PROMPT,
    format_retest_evaluation_prompt,
    format_retest_generation_prompt,
)
from app.core.config import settings, validate_llm_base_url  # noqa: E402

logger = structlog.get_logger(__name__)


def resolve_llm_credentials(
    api_key: Optional[str] = None, base_url: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    """Validate optional overrides and return (key, base_url), or None for offline fallback."""
    validated_base = validate_llm_base_url(base_url)
    cleaned_key = api_key.strip() if api_key is not None else None
    if validated_base is not None and not cleaned_key:
        return None
    key = cleaned_key if api_key is not None else settings.FREELLMAPI_API_KEY
    base = validated_base or settings.FREELLMAPI_BASE_URL
    return (key, base) if key else None


async def generate_targeted_retest_question(
    category: str,
    topic: str,
    severity: str,
    original_prompt: str,
    feedback: str,
    candidate_prior_response: Optional[str] = None,
    model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> Dict[str, str]:
    """Generate a targeted re-test question with architectural constraints and rubric."""
    fallback = get_fallback_retest_question(category, topic)
    creds = resolve_llm_credentials(llm_api_key, llm_base_url)
    if not creds:
        return fallback

    user_prompt = format_retest_generation_prompt(
        category=category,
        topic=topic,
        severity=severity,
        original_prompt=original_prompt,
        feedback=feedback,
        candidate_prior_response=candidate_prior_response,
    )

    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model=model or settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": RETEST_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                timeout=timeout_seconds,
                api_key=creds[0],
                api_base=creds[1],
            ),
            timeout=timeout_seconds,
        )
        content = response.choices[0].message.content or ""
        cleaned = clean_json_response(content)
        parsed = json.loads(cleaned)

        q_text = parsed.get("question_text") or fallback["question_text"]
        constraint = parsed.get("architectural_constraint") or fallback["architectural_constraint"]
        rubric = parsed.get("evaluation_rubric") or fallback["evaluation_rubric"]

        return {
            "question_text": q_text,
            "architectural_constraint": constraint,
            "evaluation_rubric": rubric,
        }
    except Exception as exc:
        logger.warning("retest_question_generation_failed_using_fallback", error=str(exc))
        return fallback


async def evaluate_targeted_retest_defense(
    category: str,
    topic: str,
    retest_question: str,
    constraint: str,
    rubric: str,
    candidate_response: str,
    model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> Dict[str, Any]:
    """Evaluate candidate's re-test defense against the constraint and rubric."""
    creds = resolve_llm_credentials(llm_api_key, llm_base_url)
    if not creds:
        return evaluate_retest_fallback(candidate_response, category, topic)

    user_prompt = format_retest_evaluation_prompt(
        category=category,
        topic=topic,
        retest_question=retest_question,
        constraint=constraint,
        rubric=rubric,
        candidate_response=candidate_response,
    )

    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model=model or settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": RETEST_EVALUATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                timeout=timeout_seconds,
                api_key=creds[0],
                api_base=creds[1],
            ),
            timeout=timeout_seconds,
        )
        content = response.choices[0].message.content or ""
        cleaned = clean_json_response(content)
        parsed = json.loads(cleaned)

        raw_score = float(parsed.get("score", 50.0))
        score = round(max(0.0, min(100.0, raw_score)), 1)
        passed = bool(parsed.get("passed", score >= 70.0))
        feedback = parsed.get("feedback") or "Evaluation complete."
        key_improvements = parsed.get("key_improvements") or []
        remaining_gaps = parsed.get("remaining_gaps") or []

        return {
            "score": score,
            "passed": passed,
            "feedback": feedback,
            "key_improvements": key_improvements,
            "remaining_gaps": remaining_gaps,
        }
    except Exception as exc:
        logger.warning("retest_evaluation_failed_using_fallback", error=str(exc))
        return evaluate_retest_fallback(candidate_response, category, topic)
