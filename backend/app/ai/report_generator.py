"""AI defense report generator using LiteLLM to synthesize final architectural evaluation."""

import asyncio
import json
import os
import uuid
from collections import defaultdict
from typing import Dict, List, Optional

import structlog

# Ensure LiteLLM does not attempt to download cost maps or send telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.prompts import (  # noqa: E402
    DEFENSE_REPORT_SYSTEM_PROMPT,
    format_defense_report_user_prompt,
)
from app.core.config import settings  # noqa: E402
from app.schemas.defense import DefenseSessionState  # noqa: E402
from app.schemas.question import QuestionCategory  # noqa: E402
from app.schemas.report import (  # noqa: E402
    CategoryScore,
    DefenseReportResponse,
    ReportSynthesisOutput,
)

logger = structlog.get_logger(__name__)


def aggregate_category_scores(session: DefenseSessionState) -> List[CategoryScore]:
    """Calculates mean scores and status per architectural category."""
    scores_by_cat: Dict[QuestionCategory, List[float]] = defaultdict(list)

    for prog in session.questions:
        cat = prog.question.category
        score = prog.final_score if prog.final_score is not None else prog.defense_score
        if score is not None:
            scores_by_cat[cat].append(float(score))
        else:
            scores_by_cat[cat].append(7.0)

    category_results: List[CategoryScore] = []
    for cat, score_list in scores_by_cat.items():
        mean_score = round(sum(score_list) / len(score_list), 1)
        if mean_score >= 7.5:
            st = "passed"
            summary = f"Strong command of {cat.value} tradeoffs and production constraints."
        elif mean_score >= 5.0:
            st = "remediated"
            summary = f"Sound foundation in {cat.value}, though guidance was required on scale."
        else:
            st = "needs_work"
            summary = f"Vulnerabilities identified in {cat.value}; further hardening required."

        category_results.append(
            CategoryScore(
                category=cat,
                score=mean_score,
                questions_count=len(score_list),
                status=st,
                summary=summary,
            )
        )

    # If no questions had categories, provide default
    if not category_results:
        category_results.append(
            CategoryScore(
                category=QuestionCategory.ARCHITECTURE,
                score=session.overall_score or 7.0,
                questions_count=max(session.total_questions, 1),
                status="passed",
                summary="Architectural defense completed across general repository components.",
            )
        )

    return sorted(category_results, key=lambda c: c.category.value)


def build_deterministic_fallback_report(
    session: DefenseSessionState,
    category_scores: List[CategoryScore],
) -> DefenseReportResponse:
    """Builds a deterministic, offline-resilient evaluation report."""
    score = session.overall_score
    if score is None:
        all_scores = [c.score for c in category_scores]
        score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 7.5

    if score >= 7.5:
        verdict = "Certified Principal Defense"
        summary = (
            "The candidate successfully defended the repository architecture against "
            "rigorous principal-level inquiry. They articulated core technical tradeoffs, "
            "demonstrated deep comprehension of load-bearing components, and effectively "
            "mitigated hypothetical production stress constraints."
        )
        strengths = [
            "Accurate grounding in codebase modules and dependencies without hallucination",
            "Demonstrated comprehension of production failure modes and data flow",
            "Effective architectural problem-solving during constraint stress-testing",
        ]
        blind_spots = [
            "Edge cases in rapid horizontal failover and network partition scenarios",
            "Long-term telemetry and distributed tracing considerations",
        ]
        recommendations = [
            "Implement automated load tests simulating concurrent 10k req/s traffic spikes",
            "Add distributed correlation IDs and structured circuit breaker fallbacks",
        ]
    elif score >= 5.0:
        verdict = "Solid Architectural Defense"
        summary = (
            "The candidate exhibited foundational competence across the repository codebase, "
            "answering initial questions accurately. However, they required mentor guidance "
            "when handling aggressive scalability and high-concurrency bottlenecks."
        )
        strengths = [
            "Clear understanding of primary framework and database integrations",
            "Receptiveness to mentor guidance during architectural re-testing",
        ]
        blind_spots = [
            "Underestimated database connection pool exhaustion under sudden traffic bursts",
            "Lack of proactive caching and query optimization strategies",
        ]
        recommendations = [
            "Introduce Redis caching layer with clear cache invalidation semantics",
            "Configure explicit async connection pool limits and circuit breakers",
        ]
    else:
        verdict = "Architectural Remediation Required"
        summary = (
            "The candidate struggled to defend key technical decisions and trade-offs in the "
            "codebase. Answers remained tutorial-level or superficial, revealing architectural "
            "blind spots in load-bearing modules."
        )
        strengths = [
            "Familiarity with standard repository structure and boilerplate setup",
        ]
        blind_spots = [
            "Inability to explain state synchronization and security guard mechanisms",
            "Vulnerabilities to unindexed queries and blocking synchronous operations",
        ]
        recommendations = [
            "Conduct deep-dive review of system concurrency and async event loop models",
            "Add automated unit and regression tests covering critical auth and data paths",
        ]

    return DefenseReportResponse(
        session_id=uuid.UUID(session.session_id),
        project_id=uuid.UUID(session.project_id),
        overall_score=score,
        verdict=verdict,
        summary=summary,
        category_scores=category_scores,
        key_strengths=strengths,
        critical_blind_spots=blind_spots,
        actionable_recommendations=recommendations,
        total_questions=max(session.total_questions, len(session.questions)),
        completed_at=session.updated_at,
    )


async def generate_defense_report(
    session: DefenseSessionState,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> DefenseReportResponse:
    """Generates a structured architectural defense report using LiteLLM with fallback."""
    category_scores = aggregate_category_scores(session)

    effective_model = model if model is not None else settings.LLM_MODEL
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    effective_base_url = base_url if base_url is not None else settings.FREELLMAPI_BASE_URL
    timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    if not effective_key:
        logger.warning("llm_api_key_not_configured_for_report")
        return build_deterministic_fallback_report(session, category_scores)

    # Format overview and transcript
    score_str = f"Overall Score: {session.overall_score or 7.5} / 10.0"
    cats_str = ", ".join(f"{c.category.value} ({c.score})" for c in category_scores)
    overview = f"Total Questions: {session.total_questions}\n{score_str}\nCategories: {cats_str}"

    transcript_lines = [
        f"[{t.role.upper()} - {t.stage.value}]: {t.content}"
        for t in session.turns[:25]
    ]
    transcript = "\n".join(transcript_lines) or "No dialogue recorded."

    user_prompt = format_defense_report_user_prompt(
        overview=overview,
        transcript=transcript,
    )

    try:
        messages = [
            {"role": "system", "content": DEFENSE_REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        completion_kwargs = {
            "model": effective_model,
            "messages": messages,
            "temperature": 0.2,
            "api_key": effective_key,
            "timeout": timeout,
        }
        if effective_base_url:
            completion_kwargs["api_base"] = effective_base_url

        response = await asyncio.wait_for(
            litellm.acompletion(**completion_kwargs),
            timeout=timeout,
        )
        raw_text = response.choices[0].message.content or ""
        cleaned = clean_json_response(raw_text)
        data = json.loads(cleaned)
        synthesis = ReportSynthesisOutput(**data)

        score = session.overall_score or 7.5
        return DefenseReportResponse(
            session_id=uuid.UUID(session.session_id),
            project_id=uuid.UUID(session.project_id),
            overall_score=score,
            verdict=synthesis.verdict,
            summary=synthesis.summary,
            category_scores=category_scores,
            key_strengths=synthesis.key_strengths or ["Thorough architectural grounding"],
            critical_blind_spots=synthesis.critical_blind_spots or ["Edge-case failover"],
            actionable_recommendations=synthesis.actionable_recommendations
            or ["Automated stress testing"],
            total_questions=max(session.total_questions, len(session.questions)),
            completed_at=session.updated_at,
        )
    except Exception as exc:
        logger.warning("llm_report_generation_failed_using_fallback", error=str(exc))
        return build_deterministic_fallback_report(session, category_scores)
