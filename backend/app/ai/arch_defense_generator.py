"""AI generator and Principal Architect evaluator for Architecture Defense Mode."""

import asyncio
import json
import os
from typing import Any, List, Optional, Tuple

import structlog

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.arch_defense_prompts import (  # noqa: E402
    ARCH_EVAL_SYSTEM_PROMPT,
    ARCH_GEN_SYSTEM_PROMPT,
    MAX_ANSWER_CHARS,
    MAX_DIAGRAM_CHARS,
    build_deterministic_arch_evaluation,
    build_deterministic_arch_topics,
    build_diagram_targets,
    reconcile_llm_topics,
    sanitize_xml_content,
)
from app.ai.llm import clean_json_response  # noqa: E402
from app.core.config import settings, validate_llm_base_url  # noqa: E402
from app.schemas.arch_defense import (  # noqa: E402
    ArchDefenseEvaluationOutput,
    ArchDefenseStage,
    ArchDefenseTopic,
    ArchFocusAreaType,
)
from app.schemas.architecture import ArchitectureReportResponse  # noqa: E402
from app.schemas.diagram import DiagramResponse  # noqa: E402

logger = structlog.get_logger(__name__)
_MAX_DIAGRAM_CHARS, _MAX_ANSWER_CHARS = MAX_DIAGRAM_CHARS, MAX_ANSWER_CHARS


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


async def _call_llm_json(
    system_prompt: str,
    user_prompt: str,
    creds: Tuple[str, str],
    model: Optional[str],
    timeout_seconds: float,
) -> Any:
    """Execute one structured JSON completion call through LiteLLM."""
    response = await asyncio.wait_for(
        litellm.acompletion(
            model=model or settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            timeout=timeout_seconds,
            api_key=creds[0],
            api_base=creds[1],
        ),
        timeout=timeout_seconds,
    )
    return json.loads(clean_json_response(response.choices[0].message.content or ""))


async def generate_arch_defense_topics(
    report: ArchitectureReportResponse, diagram: DiagramResponse,
    focus_area: Optional[ArchFocusAreaType] = None, max_topics: int = 4,
    model: Optional[str] = None, api_key: Optional[str] = None,
    base_url: Optional[str] = None, timeout_seconds: float = 12.0,
) -> List[ArchDefenseTopic]:
    """Synthesize diagram-grounded defense topics via LiteLLM with deterministic fallback."""
    creds = resolve_llm_credentials(api_key, base_url)
    if creds is None:
        return build_deterministic_arch_topics(report, diagram, focus_area, max_topics)

    targets = build_diagram_targets(diagram)
    ctx = {
        "project_name": report.project_name,
        "primary_pattern": report.primary_pattern.model_dump(),
        "risks": [r.model_dump() for r in report.architectural_risks[:4]],
        "nodes": [{"node_id": n.node_id, "label": n.label, "subgraph": n.subgraph}
                  for n in diagram.nodes[:15]],
        "edges": [e.model_dump() for e in diagram.edges[:20]],
        "focus_area_filter": focus_area.value if focus_area else None,
        "max_topics": max_topics,
    }
    safe_ctx = sanitize_xml_content(json.dumps(ctx, indent=2), 16000)
    safe_mermaid = sanitize_xml_content(diagram.mermaid_code, _MAX_DIAGRAM_CHARS)
    prompt = (
        f"<architecture_context>\n{safe_ctx}\n</architecture_context>\n"
        f"<diagram_mermaid>\n{safe_mermaid}\n</diagram_mermaid>"
    )
    try:
        parsed = await _call_llm_json(ARCH_GEN_SYSTEM_PROMPT, prompt, creds, model, timeout_seconds)
        items = parsed if isinstance(parsed, list) else parsed.get("topics", [])
        out = reconcile_llm_topics(items, targets, report, focus_area, max_topics)
        if out:
            return out
    except Exception as exc:
        logger.warning("arch_topic_llm_fallback", project_id=report.project_id, error=str(exc))
    return build_deterministic_arch_topics(report, diagram, focus_area, max_topics)


async def evaluate_arch_defense(
    topic: ArchDefenseTopic, candidate_answer: str, stage: ArchDefenseStage,
    model: Optional[str] = None, api_key: Optional[str] = None,
    base_url: Optional[str] = None, timeout_seconds: float = 12.0,
) -> ArchDefenseEvaluationOutput:
    """Evaluate candidate defense turn via LiteLLM with deterministic rubric fallback."""
    creds = resolve_llm_credentials(api_key, base_url)
    if creds is None:
        return build_deterministic_arch_evaluation(topic, candidate_answer, stage)
    ctx = {
        "stage": stage.value, "topic_title": topic.title, "focus_area": topic.focus_area.value,
        "design_claim": topic.design_claim, "expected_tradeoffs": topic.expected_tradeoffs,
        "target_nodes": [n.model_dump() for n in topic.target_nodes],
        "risk_references": topic.risk_references,
    }
    safe_ctx = sanitize_xml_content(json.dumps(ctx, indent=2), 16000)
    safe_answer = sanitize_xml_content(candidate_answer, _MAX_ANSWER_CHARS)
    prompt = (
        f"<architecture_context>\n{safe_ctx}\n</architecture_context>\n"
        f"<candidate_defense>\n{safe_answer}\n</candidate_defense>"
    )
    try:
        raw = await _call_llm_json(ARCH_EVAL_SYSTEM_PROMPT, prompt, creds, model, timeout_seconds)
        out = ArchDefenseEvaluationOutput.model_validate(raw)
        if stage != ArchDefenseStage.TOPIC_ACTIVE or out.is_terminal:
            out.is_terminal, out.follow_up_challenge = True, None
        return out
    except Exception as exc:
        logger.warning("arch_eval_llm_fallback", topic_id=topic.id, error=str(exc))
    return build_deterministic_arch_evaluation(topic, candidate_answer, stage)
