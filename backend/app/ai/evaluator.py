"""AI defense evaluator using LiteLLM to assess candidate claims against repository evidence."""

import asyncio
import json
import os
from typing import Optional

import structlog

# Ensure LiteLLM does not attempt to download cost maps or send telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.fallbacks import (  # noqa: E402
    build_deterministic_fallback_evaluation,
    build_deterministic_fallback_secondary,
)
from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.prompts import (  # noqa: E402
    DEFENSE_EVALUATION_SYSTEM_PROMPT,
    SECONDARY_EVALUATION_SYSTEM_PROMPT,
    format_defense_evaluation_user_prompt,
    format_secondary_evaluation_user_prompt,
)
from app.core.config import settings  # noqa: E402
from app.schemas.defense import EvaluationOutput, SecondaryEvaluationOutput  # noqa: E402
from app.schemas.question import GroundedQuestion  # noqa: E402

logger = structlog.get_logger(__name__)


async def evaluate_candidate_defense(
    question: GroundedQuestion,
    candidate_answer: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> EvaluationOutput:
    """Evaluates an initial defense answer against question evidence via LiteLLM."""
    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL
    timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
    retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    if not effective_key:
        logger.warning("llm_api_key_not_configured_for_evaluation")
        return build_deterministic_fallback_evaluation(question, candidate_answer)

    user_prompt = format_defense_evaluation_user_prompt(
        question_text=question.question_text,
        context_hint=question.context_hint,
        cited_files=question.cited_files,
        candidate_answer=candidate_answer,
    )
    messages = [
        {"role": "system", "content": DEFENSE_EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    backoff = 1.0
    for attempt in range(1, retries + 2):
        try:
            logger.info(
                "calling_litellm_defense_evaluation",
                model=effective_model,
                attempt=attempt,
                question_id=question.id,
            )

            kwargs = {
                "model": effective_model,
                "messages": messages,
                "temperature": 0.2,
                "timeout": timeout,
                "api_key": effective_key,
            }
            if effective_base_url:
                kwargs["api_base"] = effective_base_url

            response = await litellm.acompletion(**kwargs)
            raw_content = response.choices[0].message.content or ""
            cleaned = clean_json_response(raw_content)

            try:
                data = json.loads(cleaned)
                evaluation = EvaluationOutput.model_validate(data)
                logger.info(
                    "llm_defense_evaluation_success",
                    question_id=question.id,
                    passed=evaluation.passed_initial_defense,
                    depth_score=evaluation.depth_score,
                    attempt=attempt,
                )
                return evaluation
            except Exception as parse_err:
                logger.warning(
                    "llm_defense_evaluation_parse_error",
                    error=str(parse_err),
                    raw_content=raw_content[:200],
                )

        except Exception as exc:
            logger.warning(
                "llm_defense_evaluation_attempt_failed",
                attempt=attempt,
                max_retries=retries,
                error=str(exc),
            )
            if attempt <= retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                logger.error(
                    "llm_defense_evaluation_all_attempts_failed",
                    question_id=question.id,
                    error=str(exc),
                )
                return build_deterministic_fallback_evaluation(question, candidate_answer)

    return build_deterministic_fallback_evaluation(question, candidate_answer)


async def evaluate_secondary_turn(
    context_prompt: str,
    candidate_answer: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> SecondaryEvaluationOutput:
    """Evaluates a candidate's follow-up stress-test or re-test response."""
    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL
    timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
    retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    if not effective_key:
        return build_deterministic_fallback_secondary(context_prompt, candidate_answer)

    user_prompt = format_secondary_evaluation_user_prompt(
        context_prompt=context_prompt,
        candidate_answer=candidate_answer,
    )
    messages = [
        {"role": "system", "content": SECONDARY_EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    backoff = 1.0
    for attempt in range(1, retries + 2):
        try:
            kwargs = {
                "model": effective_model,
                "messages": messages,
                "temperature": 0.2,
                "timeout": timeout,
                "api_key": effective_key,
            }
            if effective_base_url:
                kwargs["api_base"] = effective_base_url

            response = await litellm.acompletion(**kwargs)
            raw_content = response.choices[0].message.content or ""
            cleaned = clean_json_response(raw_content)

            try:
                data = json.loads(cleaned)
                return SecondaryEvaluationOutput.model_validate(data)
            except Exception as parse_err:
                logger.warning(
                    "llm_secondary_evaluation_parse_error",
                    error=str(parse_err),
                    raw_content=raw_content[:200],
                )

        except Exception as exc:
            logger.warning("llm_secondary_evaluation_attempt_failed", error=str(exc))
            if attempt <= retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                return build_deterministic_fallback_secondary(context_prompt, candidate_answer)

    return build_deterministic_fallback_secondary(context_prompt, candidate_answer)
