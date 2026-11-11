"""AI generator and evaluator for stress test scaling scenarios using LiteLLM."""

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.core.config import settings, validate_llm_base_url  # noqa: E402
from app.schemas.stress_test import (  # noqa: E402
    StressConstraintType,
    StressEvaluationOutput,
    StressSessionStage,
    StressSeverity,
    StressTarget,
    StressTestScenario,
)

logger = structlog.get_logger(__name__)

STRESS_GEN_SYSTEM_PROMPT = """You are a Principal Infrastructure Architect.
Inspect candidate codebase components and synthesize extreme scaling scenarios.
Evaluate code for 50k req/sec spikes, 100x table growth, DB starvation, or OOM.
Enclose context in XML tags. Return a valid JSON list conforming to:
[
  {
    "title": "Scenario Title",
    "constraint_type": "CONCURRENCY_SPIKE|DATA_VOLUME_100X|...",
    "severity": "MODERATE|SEVERE|EXTREME",
    "target": {
      "symbol_name": "target_name",
      "file_path": "path/to/file",
      "line_range": "10-50",
      "component_type": "endpoint|model|cache|worker"
    },
    "context_description": "Nominal behavior summary",
    "hypothetical_prompt": "Principal Architect what-if prompt interrogating limits",
    "expected_tradeoffs": ["Tradeoff 1", "Tradeoff 2"]
  }
]"""

STRESS_EVAL_SYSTEM_PROMPT = """You are a rigorous Principal Infrastructure Architect.
Assess whether candidate:
1. Accurately identified the failure point / bottleneck.
2. Formulated a concrete scaling strategy (caching, connection pooling, queues).
3. Acknowledged real-world tradeoffs (cache invalidation, consistency vs cost).
Return a valid JSON object conforming to:
{
  "depth_score": 8,
  "bottleneck_identified": true,
  "scaling_strategy_sound": true,
  "tradeoffs_acknowledged": true,
  "feedback": "Principal Architect evaluation notes",
  "follow_up_constraint": "Secondary stress constraint if advancing, or null",
  "is_terminal": false
}"""


def build_deterministic_stress_scenarios(
    project_name: str,
    evidence_items: Optional[List[Dict[str, Any]]] = None,
    constraint_type: Optional[StressConstraintType] = None,
    max_scenarios: int = 4,
) -> List[StressTestScenario]:
    """Generates deterministic, evidence-grounded stress scenarios without remote LLM calls."""
    evidence_list = evidence_items or []
    first = evidence_list[0] if evidence_list else None
    target_file = first.get("file_path", "app/api/v1/router.py") if first else "app/main.py"
    target_sym = first.get("symbol_name", "handle_request") if first else "app_router"

    all_specs = [
        (
            StressConstraintType.CONCURRENCY_SPIKE,
            f"Concurrency Spike on {target_sym}",
            "Traffic spikes 100x to 25,000 req/sec during a flash event.",
            f"Suppose 25k req/sec hit {target_sym} in {target_file}. How do you avoid starvation?",
            ["Latency degradation", "Overprovisioning costs"],
        ),
        (
            StressConstraintType.DB_CONNECTION_STARVATION,
            f"Connection Pool Saturation in {project_name}",
            "Max connection limit reached; queries queue up and timeout.",
            f"Database pool is clamped at 20. How does {target_sym} handle connection timeouts?",
            ["Connection pooling overhead", "Stale connection churn"],
        ),
        (
            StressConstraintType.DATA_VOLUME_100X,
            f"100x Data Volume Explosion on {target_sym}",
            "Data volume increases from 10k to 10M rows, causing table scans.",
            f"If table size reaches 10M rows, how do you prevent table scans in {target_sym}?",
            ["Index write overhead", "Memory usage for large result sets"],
        ),
        (
            StressConstraintType.MEMORY_PRESSURE,
            f"Memory Pressure & OOM Constraints on {target_sym}",
            "Container memory is capped at 256MB under peak payload processing.",
            f"Under strict 256MB RAM limits, how do you process data in {target_sym} without OOM?",
            ["Throughput throttling", "Streaming complexity"],
        ),
        (
            StressConstraintType.NETWORK_LATENCY_JITTER,
            f"Tail Latency & Packet Jitter on {target_sym}",
            "Upstream RPC latency spikes to 2,500ms p99 with 15% packet loss.",
            f"Under 2.5s jitter, how does {target_sym} in {target_file} avoid timeouts?",
            ["Aggressive timeout drops", "Retry storm amplification"],
        ),
    ]

    selected = [s for s in all_specs if constraint_type is None or s[0] == constraint_type]
    scenarios: List[StressTestScenario] = []
    for c_type, title, ctx, prompt, tradeoffs in selected[:max_scenarios]:
        scenarios.append(
            StressTestScenario(
                id=str(uuid.uuid4()),
                title=title,
                constraint_type=c_type,
                severity=StressSeverity.SEVERE,
                target=StressTarget(
                    symbol_name=target_sym,
                    file_path=target_file,
                    line_range="1-50",
                    component_type="endpoint" if "api" in target_file else "model",
                ),
                context_description=ctx,
                hypothetical_prompt=prompt,
                expected_tradeoffs=tradeoffs,
                cited_evidence_ids=[str(e.get("id")) for e in evidence_list[:2] if e.get("id")],
            )
        )
    return scenarios


def build_deterministic_stress_evaluation(
    scenario: StressTestScenario,
    answer: str,
    stage: StressSessionStage = StressSessionStage.SCENARIO_ACTIVE,
) -> StressEvaluationOutput:
    """Evaluates candidate response deterministically using architectural heuristics."""
    ans_lower = answer.lower()
    keywords = ("pool", "cache", "redis", "async", "index", "replica", "queue", "circuit", "limit")
    matches = sum(1 for kw in keywords if kw in ans_lower)
    identified = len(answer.strip()) > 30 and matches >= 1
    sound = matches >= 2
    tradeoffs = any(k in ans_lower for k in ["tradeoff", "cost", "latency"]) or matches >= 3

    if matches >= 3 and len(answer) > 80:
        score = 8
        feedback = (
            "Strong architectural defense: recognized the bottleneck "
            "and proposed actionable scaling mitigations."
        )
    elif matches >= 1:
        score = 6
        feedback = (
            "Adequate scaling awareness, though specific pooling limits "
            "or caching invalidation should be specified."
        )
    else:
        score = 4
        feedback = (
            "Superficial defense: failed to pinpoint the architectural "
            "bottleneck or concrete mitigation strategy."
        )

    is_term = not (stage == StressSessionStage.SCENARIO_ACTIVE and score >= 6)
    follow_up = (
        None
        if is_term
        else (
            "What happens if your Redis cache experiences eviction thrashing "
            "or network partition during this peak?"
        )
    )
    return StressEvaluationOutput(
        depth_score=score,
        bottleneck_identified=identified,
        scaling_strategy_sound=sound,
        tradeoffs_acknowledged=tradeoffs,
        feedback=feedback,
        follow_up_constraint=follow_up,
        is_terminal=is_term,
    )


def _resolve_llm_credentials(
    api_key: Optional[str], base_url: Optional[str]
) -> Optional[Tuple[str, str]]:
    """Validate overrides and return (key, base_url), or None for offline fallback."""
    validated_base = validate_llm_base_url(base_url)
    if validated_base is not None and api_key is None:
        return None
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    if not effective_key:
        return None
    return effective_key, validated_base or settings.FREELLMAPI_BASE_URL


async def generate_stress_scenarios(
    project_name: str,
    evidence_items: Optional[List[Dict[str, Any]]] = None,
    constraint_type: Optional[StressConstraintType] = None,
    max_scenarios: int = 4,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> List[StressTestScenario]:
    """Generates scaling stress test scenarios using LiteLLM or deterministic fallback."""
    creds = _resolve_llm_credentials(api_key, base_url)
    if creds is None:
        return build_deterministic_stress_scenarios(
            project_name, evidence_items, constraint_type, max_scenarios
        )

    effective_key, effective_base = creds
    effective_model = model or settings.LLM_MODEL
    ev_text = json.dumps(evidence_items or [], indent=2)
    user_prompt = (
        f"Project: {project_name}\nConstraint Filter: {constraint_type}\n"
        f"<evidence_context>\n{ev_text}\n</evidence_context>"
    )

    try:
        resp = await litellm.acompletion(
            model=effective_model,
            messages=[
                {"role": "system", "content": STRESS_GEN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            api_key=effective_key,
            base_url=effective_base,
            temperature=0.3,
            timeout=10.0,
        )
        raw = resp.choices[0].message.content or "[]"
        parsed = json.loads(clean_json_response(raw))
        if isinstance(parsed, list) and parsed:
            return [StressTestScenario.model_validate(item) for item in parsed[:max_scenarios]]
    except Exception as exc:
        logger.warning("stress_scenario_gen_fallback", error=str(exc))

    return build_deterministic_stress_scenarios(
        project_name, evidence_items, constraint_type, max_scenarios
    )


async def evaluate_stress_defense(
    scenario: StressTestScenario,
    candidate_answer: str,
    stage: StressSessionStage = StressSessionStage.SCENARIO_ACTIVE,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> StressEvaluationOutput:
    """Evaluates candidate response to scaling constraint using LiteLLM or fallback."""
    creds = _resolve_llm_credentials(api_key, base_url)
    if creds is None:
        return build_deterministic_stress_evaluation(scenario, candidate_answer, stage)

    effective_key, effective_base = creds
    effective_model = model or settings.LLM_MODEL
    user_prompt = (
        f"Scenario: {scenario.title}\nConstraint: {scenario.constraint_type.value}\n"
        f"Prompt: {scenario.hypothetical_prompt}\nStage: {stage.value}\n"
        f"<candidate_defense>\n{candidate_answer}\n</candidate_defense>"
    )

    try:
        resp = await litellm.acompletion(
            model=effective_model,
            messages=[
                {"role": "system", "content": STRESS_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            api_key=effective_key,
            base_url=effective_base,
            temperature=0.2,
            timeout=10.0,
        )
        raw = resp.choices[0].message.content or "{}"
        parsed = json.loads(clean_json_response(raw))
        return StressEvaluationOutput.model_validate(parsed)
    except Exception as exc:
        logger.warning("stress_eval_fallback", error=str(exc))

    return build_deterministic_stress_evaluation(scenario, candidate_answer, stage)
