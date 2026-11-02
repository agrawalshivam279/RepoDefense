"""LiteLLM wrapper for structured OpenAI-compatible LLM routing and resilience."""

import asyncio
import json
import os
import re
from typing import Optional

import structlog

# Ensure LiteLLM does not attempt to download cost maps or send telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.prompts import (  # noqa: E402
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    format_project_summary_user_prompt,
)
from app.core.config import settings  # noqa: E402
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


def build_deterministic_fallback_summary(meta: ProjectSummaryInput) -> ProjectSummary:
    """Constructs a deterministic, evidence-grounded summary when LLM is unavailable."""
    primary_lang = "Unknown"
    if meta.top_languages:
        # e.g., "Python (15)" -> "Python"
        primary_lang = meta.top_languages[0].split("(")[0].strip()

    title = f"{meta.project_name} Codebase Overview"
    tagline = f"Software project in {primary_lang} with {meta.total_files} analyzed files."

    style = "Modular Application"
    dep_text = " ".join(d.lower() for d in meta.dependencies)
    if any(k in dep_text for k in ["fastapi", "express", "flask"]):
        style = "REST API Service"
    elif any(k in dep_text for k in ["next", "react"]):
        style = "Full-Stack Web Application"

    known_frameworks = ["fastapi", "flask", "django", "next", "react", "express", "torch"]
    frameworks = [
        dep for dep in meta.dependencies
        if any(fw in dep.lower() for fw in known_frameworks)
    ][:5]

    components = meta.evidence_tags[:5] if meta.evidence_tags else ["Core Application Logic"]
    sample_deps = ", ".join(meta.dependencies[:3]) if meta.dependencies else primary_lang

    defense_topics = [
        f"Scalability and dependency lifecycle for primary packages ({sample_deps})",
        "Error handling, input validation, and boundary exception safety across modules",
    ]

    top_authors = (
        ", ".join(meta.top_contributors[:2])
        if meta.top_contributors
        else "the project team"
    )

    narrative = (
        f"{meta.project_name} contains {meta.total_files} source files totaling "
        f"{meta.total_lines} lines of code. The primary language is {primary_lang}. "
        f"Key detected architectural components include: {', '.join(components)}. "
        f"Recent contributions reflect active development led by {top_authors}."
    )

    return ProjectSummary(
        title=title,
        tagline=tagline,
        primary_language=primary_lang,
        detected_frameworks=frameworks,
        architectural_style=style,
        key_components=components,
        potential_defense_topics=defense_topics,
        narrative=narrative,
    )


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
