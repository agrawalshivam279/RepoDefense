"""AI-driven synthesizer and evaluation engine for Mentor Mode Mini Challenges."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional

import structlog
from litellm import acompletion

from app.ai.challenge_fallbacks import (
    build_fallback_challenge,
    build_fallback_evaluation,
)
from app.ai.challenge_prompts import (
    CHALLENGE_EVALUATION_SYSTEM_PROMPT,
    MINI_CHALLENGE_SYSTEM_PROMPT,
    format_challenge_evaluation_prompt,
    format_challenge_generation_prompt,
)
from app.core.config import settings
from app.schemas.challenge import (
    ChallengeEvaluationResponse,
    MiniChallengeDifficulty,
    MiniChallengeResponse,
)

logger = structlog.get_logger(__name__)


def _clean_json_response(content: str) -> Dict[str, Any]:
    """Extract and parse structured JSON from LLM output safely."""
    raw = content.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        raw = match.group(1).strip()
    return json.loads(raw)


async def generate_mini_challenge(
    category: str,
    topic: str,
    difficulty: MiniChallengeDifficulty = MiniChallengeDifficulty.INTERMEDIATE,
    language: str = "python",
    question_prompt: Optional[str] = None,
    candidate_response: Optional[str] = None,
    feedback: Optional[str] = None,
    code_context: Optional[str] = None,
    model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> MiniChallengeResponse:
    """Synthesize a targeted architectural mini-challenge using LiteLLM with fallback."""
    user_prompt = format_challenge_generation_prompt(
        category=category,
        topic=topic,
        difficulty=difficulty.value,
        language=language,
        question_prompt=question_prompt,
        candidate_response=candidate_response,
        feedback=feedback,
        code_context=code_context,
    )

    selected_model = model or settings.LLM_MODEL
    api_key = llm_api_key if llm_api_key is not None else settings.FREELLMAPI_API_KEY
    base_url = llm_base_url or settings.FREELLMAPI_BASE_URL

    if not api_key:
        logger.info("mini_challenge_using_deterministic_fallback", topic=topic)
        return build_fallback_challenge(category, topic, difficulty, language)

    try:
        kwargs: Dict[str, Any] = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": MINI_CHALLENGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "timeout": 25.0,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        resp = await acompletion(**kwargs)
        raw_text = resp.choices[0].message.content or ""
        parsed = _clean_json_response(raw_text)

        return MiniChallengeResponse(
            category=category,
            topic=topic,
            difficulty=difficulty,
            title=str(parsed.get("title", f"Challenge: {topic}")),
            scenario=str(parsed.get("scenario", "Architectural challenge scenario")),
            starter_code=parsed.get("starter_code"),
            language=language,
            requirements=list(parsed.get("requirements", [])),
            hints=list(parsed.get("hints", [])),
        )
    except Exception as exc:
        logger.warning("mini_challenge_llm_failed_falling_back", error=str(exc))
        return build_fallback_challenge(category, topic, difficulty, language)


async def evaluate_mini_challenge(
    challenge_id: uuid.UUID,
    category: str,
    topic: str,
    scenario: str,
    requirements: List[str],
    candidate_solution: str,
    language: str = "python",
    model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> ChallengeEvaluationResponse:
    """Evaluate candidate's solution using LiteLLM with deterministic fallback."""
    user_prompt = format_challenge_evaluation_prompt(
        category=category,
        topic=topic,
        scenario=scenario,
        requirements=requirements,
        candidate_solution=candidate_solution,
        language=language,
    )

    selected_model = model or settings.LLM_MODEL
    api_key = llm_api_key if llm_api_key is not None else settings.FREELLMAPI_API_KEY
    base_url = llm_base_url or settings.FREELLMAPI_BASE_URL

    if not api_key:
        return build_fallback_evaluation(challenge_id, candidate_solution, requirements)

    try:
        kwargs: Dict[str, Any] = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": CHALLENGE_EVALUATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "timeout": 25.0,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        resp = await acompletion(**kwargs)
        raw_text = resp.choices[0].message.content or ""
        parsed = _clean_json_response(raw_text)

        score = float(parsed.get("score", 50.0))
        passed = bool(parsed.get("passed", score >= 75.0))

        return ChallengeEvaluationResponse(
            challenge_id=challenge_id,
            passed=passed,
            score=max(0.0, min(100.0, score)),
            strengths=list(parsed.get("strengths", [])),
            missing_elements=list(parsed.get("missing_elements", [])),
            critique=str(parsed.get("critique", "Evaluation completed.")),
            model_solution=str(parsed.get("model_solution", "")),
        )
    except Exception as exc:
        logger.warning("challenge_eval_llm_failed_falling_back", error=str(exc))
        return build_fallback_evaluation(challenge_id, candidate_solution, requirements)
