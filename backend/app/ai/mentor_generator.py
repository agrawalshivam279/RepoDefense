"""AI generator and Principal Mentor engine for teaching content and code remediation."""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import structlog

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.mentor_prompts import (  # noqa: E402
    MENTOR_SYSTEM_PROMPT,
    build_deterministic_mentor_explanation,
    build_mentor_user_prompt,
)
from app.core.config import settings, validate_llm_base_url  # noqa: E402
from app.schemas.mentor import (  # noqa: E402
    CodeRemediationSnippet,
    MentorExplanationResponse,
)

logger = structlog.get_logger(__name__)

# Alias for backwards compatibility with existing unit tests
_build_deterministic_mentor_explanation = build_deterministic_mentor_explanation


def resolve_llm_credentials(
    api_key: Optional[str], base_url: Optional[str]
) -> Optional[Tuple[str, str]]:
    """Validate optional overrides and return (key, base_url), or None for offline fallback."""
    validated_base = validate_llm_base_url(base_url)
    cleaned_key = api_key.strip() if api_key is not None else None
    if validated_base is not None and not cleaned_key:
        return None
    key = cleaned_key if api_key is not None else settings.FREELLMAPI_API_KEY
    base = validated_base or settings.FREELLMAPI_BASE_URL
    return (key, base) if key else None


async def generate_mentor_explanation(
    category: str,
    topic: str,
    question_prompt: Optional[str] = None,
    candidate_response: Optional[str] = None,
    feedback: Optional[str] = None,
    code_context: Optional[str] = None,
    language: str = "python",
    model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> MentorExplanationResponse:
    """Generate structured architectural teaching content with Before/After code remediation."""
    creds = resolve_llm_credentials(llm_api_key, llm_base_url)
    if not creds:
        logger.info("mentor_offline_fallback", reason="No valid LLM credentials or base URL")
        return build_deterministic_mentor_explanation(category, topic, language, feedback)

    user_prompt = build_mentor_user_prompt(
        category, topic, question_prompt, candidate_response, feedback, code_context, language
    )

    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model=model or settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": MENTOR_SYSTEM_PROMPT},
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

        examples = [
            CodeRemediationSnippet(
                title=item.get("title", f"Remediation for {topic}"),
                language=item.get("language", language),
                file_context=item.get("file_context"),
                before_code=item.get("before_code", "# Original code"),
                after_code=item.get("after_code", "# Remediated code"),
                explanation=item.get("explanation", "Architectural improvement."),
            )
            for item in parsed.get("code_examples", [])
        ]
        if not examples:
            examples = build_deterministic_mentor_explanation(
                category, topic, language, feedback
            ).code_examples

        return MentorExplanationResponse(
            explanation_id=uuid.uuid4(),
            category=parsed.get("category", category),
            topic=parsed.get("topic", topic),
            architectural_risk=parsed.get("architectural_risk", "Identified design risk."),
            core_concept=parsed.get("core_concept", "Fundamental Design Principle"),
            mentor_advice=parsed.get("mentor_advice", "Review architectural best practices."),
            code_examples=examples,
            key_takeaways=parsed.get(
                "key_takeaways",
                ["Verify resource limits.", "Enforce deterministic lifecycle management."],
            ),
            socratic_followup=parsed.get(
                "socratic_followup",
                f"How would you verify the resilience of your {topic} implementation?",
            ),
            generated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.warning("mentor_generation_failed_using_fallback", error=str(exc))
        return build_deterministic_mentor_explanation(category, topic, language, feedback)
