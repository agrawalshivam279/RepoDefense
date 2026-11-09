"""Chaos scenario generator and SRE incident defense evaluation engine."""

import json
import uuid
from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.schemas.incident import (
    ChaosTarget,
    FailureCategory,
    IncidentScenario,
    IncidentSeverity,
    IncidentStage,
)

logger = structlog.get_logger(__name__)

INCIDENT_SRE_SYSTEM_PROMPT = (
    "You are a Principal Site Reliability Engineer (SRE) and Chaos Architect.\n"
    "Your goal is to stress-test how a candidate's codebase handles real-world outages.\n"
    "Ground all failure scenarios strictly in the provided code evidence.\n"
    "Always respond in valid JSON conforming to the requested schema."
)


def _build_deterministic_scenarios(
    evidence_items: List[Dict[str, Any]],
    category: Optional[FailureCategory] = None,
    limit: int = 3,
) -> List[IncidentScenario]:
    """Deterministically synthesize realistic chaos scenarios based on discovered evidence."""
    # Map candidate anchors from evidence
    db_anchor = next(
        (
            e
            for e in evidence_items
            if any(k in str(e).lower() for k in ["db", "database", "sql", "model"])
        ),
        {
            "file_path": "backend/app/core/database.py",
            "symbol_name": "get_db",
            "type": "database",
        },
    )
    api_anchor = next(
        (
            e
            for e in evidence_items
            if any(k in str(e).lower() for k in ["api", "router", "client", "http", "fetch"])
        ),
        {
            "file_path": "backend/app/api/v1/projects.py",
            "symbol_name": "create_project",
            "type": "endpoint",
        },
    )
    worker_anchor = next(
        (
            e
            for e in evidence_items
            if any(k in str(e).lower() for k in ["worker", "job", "queue", "arq", "redis"])
        ),
        {
            "file_path": "backend/app/workers/cloner.py",
            "symbol_name": "clone_repo_worker",
            "type": "worker",
        },
    )

    catalog: List[IncidentScenario] = [
        IncidentScenario(
            id=str(uuid.uuid4()),
            title="Database Connection Pool Starvation Under Surge",
            category=FailureCategory.DATABASE_OUTAGE,
            severity=IncidentSeverity.P0_CRITICAL,
            hypothetical_trigger=(
                "Traffic surges to 3,500 req/sec while an unindexed query locks the primary table."
            ),
            symptoms=[
                "FastAPI connections hang waiting for database connection checkout",
                "HTTP 504 Gateway Timeout spike on edge ingress",
                "QueuePool limit of size 20 overflow 10 reached",
            ],
            grounded_target=ChaosTarget(
                file_path=db_anchor.get("file_path", "backend/app/core/database.py"),
                symbol_name=db_anchor.get("symbol_name", "get_db"),
                component_type="database",
            ),
            incident_question=(
                "Under traffic saturation, client requests pool out waiting for connections. "
                f"Looking at `{db_anchor.get('file_path', 'database.py')}`, how does your code "
                "handle connection timeouts and what backpressure mechanism prevents crashing?"
            ),
            evaluation_criteria=[
                "Configuring finite pool timeout and max overflow limits",
                "Implementing circuit breakers to fail fast instead of hanging",
                "Read-write splitting or read-through caching for high-frequency queries",
                "Graceful degradation with client-side retry budgets and exponential backoff",
            ],
        ),
        IncidentScenario(
            id=str(uuid.uuid4()),
            title="Upstream API Latency Cascades & Thread Exhaustion",
            category=FailureCategory.DEPENDENCY_TIMEOUT,
            severity=IncidentSeverity.P1_HIGH,
            hypothetical_trigger="Third-party service response latency jumps from 120ms to 45s.",
            symptoms=[
                "Event loop task saturation and rising memory consumption",
                "Client-side connection timeouts and cascading retries",
                "Upstream 502/504 errors propagating to frontend users",
            ],
            grounded_target=ChaosTarget(
                file_path=api_anchor.get("file_path", "backend/app/api/v1/projects.py"),
                symbol_name=api_anchor.get("symbol_name", "api_handler"),
                component_type="endpoint",
            ),
            incident_question=(
                "The upstream third-party service latency has skyrocketed. "
                f"Examining `{api_anchor.get('file_path', 'api.py')}`, how do you prevent slow "
                "upstream calls from exhausting worker concurrency?"
            ),
            evaluation_criteria=[
                "Strict per-request HTTP timeout enforcement (e.g. 3-5 seconds max)",
                "Circuit breaker pattern to short-circuit calls when upstream fails",
                "Asynchronous background decoupling rather than inline synchronous blocking",
                "Serving stale or degraded fallback responses",
            ],
        ),
        IncidentScenario(
            id=str(uuid.uuid4()),
            title="Asynchronous Task Queue Saturation & Poison Pill Starvation",
            category=FailureCategory.MESSAGE_BROKER_PARTITION,
            severity=IncidentSeverity.P1_HIGH,
            hypothetical_trigger="Malformed job payload causes workers to crash in a retry loop.",
            symptoms=[
                "Queue backlog climbing past 50,000 unacknowledged jobs",
                "Worker node CPU pinned at 100% due to crash loop backoff",
                "Healthy background processing stalled indefinitely",
            ],
            grounded_target=ChaosTarget(
                file_path=worker_anchor.get("file_path", "backend/app/workers/cloner.py"),
                symbol_name=worker_anchor.get("symbol_name", "worker_process"),
                component_type="worker",
            ),
            incident_question=(
                "A corrupted payload triggers repeated worker crashes, blocking the entire queue. "
                f"In `{worker_anchor.get('file_path', 'worker.py')}`, how do you isolate poison "
                "pills and what retry limits ensure overall pipeline liveness?"
            ),
            evaluation_criteria=[
                "Dead Letter Queue (DLQ) for unprocessable jobs exceeding max attempts",
                "Defensive payload deserialization and validation before execution",
                "Worker healthcheck liveness probes with graceful job requeueing",
                "Idempotency tokens to ensure retried tasks don't corrupt state",
            ],
        ),
    ]

    if category:
        catalog = [s for s in catalog if s.category == category] or catalog

    return catalog[:limit]


async def generate_incident_scenarios(
    evidence_items: List[Dict[str, Any]],
    category: Optional[FailureCategory] = None,
    limit: int = 3,
) -> List[IncidentScenario]:
    """Generate grounded chaos scenarios using LiteLLM with deterministic fallback."""
    if not settings.FREELLMAPI_API_KEY:
        return _build_deterministic_scenarios(evidence_items, category, limit)

    try:
        from litellm import acompletion

        prompt = (
            f"Generate {limit} realistic production incident scenarios based on code evidence.\n"
            f"<code_evidence>\n{json.dumps(evidence_items[:8], indent=2)}\n</code_evidence>\n"
            f"Category Filter: {category.value if category else 'ANY'}\n"
            "Return JSON matching list of scenarios: title, category, severity, "
            "hypothetical_trigger, symptoms, grounded_target, incident_question, criteria."
        )

        response = await acompletion(
            model=settings.LLM_MODEL or "openai/auto",
            api_base=settings.FREELLMAPI_BASE_URL,
            api_key=settings.FREELLMAPI_API_KEY,
            messages=[
                {"role": "system", "content": INCIDENT_SRE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=10,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        raw_scenarios = data.get("scenarios", data if isinstance(data, list) else [])
        parsed = [IncidentScenario.model_validate(s) for s in raw_scenarios]
        return (
            parsed[:limit]
            if parsed
            else _build_deterministic_scenarios(evidence_items, category, limit)
        )
    except Exception as exc:
        logger.warning(
            "LLM incident generation failed; utilizing deterministic fallback", error=str(exc)
        )
        return _build_deterministic_scenarios(evidence_items, category, limit)


def evaluate_incident_defense_turn(
    scenario: IncidentScenario,
    turn_index: int,
    max_turns: int,
    candidate_answer: str,
) -> Dict[str, Any]:
    """Evaluate candidate defense against failure modes and generate escalation or postmortem."""
    ans_lower = candidate_answer.lower()
    resilience_keywords = [
        "circuit breaker", "timeout", "retry", "backoff", "pool", "dead letter",
        "dlq", "cache", "fallback", "degrade", "bulkhead", "idempotent", "rate limit",
        "semaphore", "queue", "healthcheck", "replica", "partition", "isolate"
    ]
    matched = [k for k in resilience_keywords if k in ans_lower]
    keyword_score = min(100.0, max(35.0, len(matched) * 16.0 + (len(candidate_answer) / 30.0)))
    score = round(min(98.0, keyword_score), 1)

    if turn_index == 1:
        patterns = ", ".join(matched[:3]) if matched else "basic safeguards"
        feedback = (
            f"Candidate identified {len(matched)} key resilience patterns ({patterns}). "
            f"Baseline architectural posture scored {score}/100."
        )
        escalation = (
            "CHAOS ESCALATION: Your initial mitigation reduced primary failure rate, but the retry "
            "surge amplified downstream load, spiking secondary queue latency by 400%. "
            "How do you implement retry budgets and exponential backoff with jitter?"
        )
        next_prompt = escalation
        next_stage = IncidentStage.ESCALATED
    elif turn_index == 2:
        feedback = (
            f"Candidate addressed cascading load with score {score}/100. "
            "Demonstrated awareness of retry amplification and backpressure controls."
        )
        escalation = (
            "INCIDENT MITIGATION COMPLETE. The immediate blast radius has been contained. "
            "Please provide a formal Engineering Postmortem: What code refactors and alert "
            "thresholds ensure this failure mode is permanently prevented?"
        )
        next_prompt = escalation
        next_stage = IncidentStage.MITIGATED
    else:
        feedback = (
            f"Postmortem evaluated with depth score {score}/100. Prevention strategy formulated."
        )
        next_prompt = "Incident defense completed."
        next_stage = IncidentStage.POSTMORTEM

    return {
        "score": score,
        "feedback": feedback,
        "escalation_injected": next_prompt if turn_index < max_turns else None,
        "next_prompt": next_prompt,
        "next_stage": next_stage,
    }
