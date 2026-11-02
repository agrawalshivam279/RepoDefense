"""LiteLLM wrapper for structured OpenAI-compatible LLM routing and resilience."""

import asyncio
import json
import os
import re
from typing import List, Optional

import structlog

# Ensure LiteLLM does not attempt to download cost maps or send telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.fallbacks import (  # noqa: E402
    build_deterministic_fallback_questions,
    build_deterministic_fallback_summary,
)
from app.ai.prompts import (  # noqa: E402
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    format_project_summary_user_prompt,
    format_question_generation_user_prompt,
)
from app.core.config import settings  # noqa: E402
from app.schemas.question import (  # noqa: E402
    GroundedQuestion,
    QuestionGenerationInput,
)
from app.schemas.summary import ProjectSummary, ProjectSummaryInput  # noqa: E402

logger = structlog.get_logger(__name__)

_JSON_BLOCK_PATTERN = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)


def clean_json_response(raw_text: str) -> str:
    """Strips markdown code fences and extraneous whitespace from model response."""
    text = raw_text.strip()
    match = _JSON_BLOCK_PATTERN.match(text)
    if match:
        return match.group(1).strip()
    return text


async def generate_project_summary(
    meta: ProjectSummaryInput,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> ProjectSummary:
    """Generates an evidence-grounded ProjectSummary via LiteLLM with retries and fallback."""
    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL
    timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
    retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    if not effective_key:
        logger.warning("llm_api_key_not_configured_using_fallback", project=meta.project_name)
        return build_deterministic_fallback_summary(meta)

    user_prompt = format_project_summary_user_prompt(meta)
    messages = [
        {"role": "system", "content": PROJECT_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    backoff = 1.0
    for attempt in range(1, retries + 2):
        try:
            logger.info(
                "calling_litellm_project_summary",
                model=effective_model,
                attempt=attempt,
                project=meta.project_name,
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
                summary = ProjectSummary.model_validate_json(cleaned)
                logger.info(
                    "llm_project_summary_success",
                    project=meta.project_name,
                    title=summary.title,
                    attempt=attempt,
                )
                return summary
            except Exception as parse_err:
                logger.warning(
                    "llm_project_summary_json_parse_error",
                    error=str(parse_err),
                    raw_content=raw_content[:200],
                )
                data = json.loads(cleaned)
                return ProjectSummary.model_validate(data)

        except Exception as exc:
            logger.warning(
                "llm_project_summary_attempt_failed",
                attempt=attempt,
                max_retries=retries,
                error=str(exc),
            )
            if attempt <= retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                logger.error(
                    "llm_project_summary_all_attempts_failed_using_fallback",
                    project=meta.project_name,
                    error=str(exc),
                )
                return build_deterministic_fallback_summary(meta)

    return build_deterministic_fallback_summary(meta)


async def generate_grounded_questions(
    input_data: QuestionGenerationInput,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> List[GroundedQuestion]:
    """Generates evidence-grounded interview questions via LiteLLM with retries and fallback."""
    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL
    timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
    retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    if not effective_key:
        logger.warning("llm_api_key_not_configured_for_questions", project=input_data.project_name)
        return build_deterministic_fallback_questions(input_data)

    user_prompt = format_question_generation_user_prompt(input_data)
    messages = [
        {"role": "system", "content": QUESTION_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    backoff = 1.0
    for attempt in range(1, retries + 2):
        try:
            logger.info(
                "calling_litellm_question_generation",
                model=effective_model,
                attempt=attempt,
                project=input_data.project_name,
            )

            kwargs = {
                "model": effective_model,
                "messages": messages,
                "temperature": 0.3,
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
                if isinstance(data, dict) and "questions" in data:
                    data = data["questions"]
                if not isinstance(data, list):
                    raise ValueError("Expected JSON array of question objects")

                parsed_questions: list[GroundedQuestion] = []
                for item in data:
                    q = GroundedQuestion.model_validate(item)
                    parsed_questions.append(q)

                if parsed_questions:
                    logger.info(
                        "llm_question_generation_success",
                        project=input_data.project_name,
                        count=len(parsed_questions),
                        attempt=attempt,
                    )
                    return parsed_questions[:input_data.requested_count]

            except Exception as parse_err:
                logger.warning(
                    "llm_question_generation_parse_error",
                    error=str(parse_err),
                    raw_content=raw_content[:200],
                )

        except Exception as exc:
            logger.warning(
                "llm_question_generation_attempt_failed",
                attempt=attempt,
                max_retries=retries,
                error=str(exc),
            )
            if attempt <= retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                logger.error(
                    "llm_question_generation_all_attempts_failed",
                    project=input_data.project_name,
                    error=str(exc),
                )
                return build_deterministic_fallback_questions(input_data)

    return build_deterministic_fallback_questions(input_data)
