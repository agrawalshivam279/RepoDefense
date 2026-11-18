"""Deterministic offline fallbacks for Targeted Re-Testing."""

import re
from typing import Any, Dict, List

_CATEGORY_FALLBACKS: Dict[str, Dict[str, str]] = {
    "concurrency": {
        "question_text": (
            "In high-concurrency workloads where multiple worker instances attempt simultaneous "
            "state transitions on the same resource, how do you prevent lost updates and deadlocks "
            "without causing severe lock contention?"
        ),
        "architectural_constraint": (
            "10,000 concurrent transactions per second contending on shared database rows."
        ),
        "evaluation_rubric": (
            "Candidate must explain optimistic concurrency control (version checks), "
            "row-level locks with timeouts, or idempotent queues."
        ),
    },
    "caching": {
        "question_text": (
            "When invalidating cache entries across a distributed cache cluster during continuous "
            "high-velocity writes, how do you guarantee cache consistency while preventing cache "
            "stampede on expiration?"
        ),
        "architectural_constraint": (
            "Cache hit ratio must remain >95% even during sudden key invalidation spikes."
        ),
        "evaluation_rubric": (
            "Candidate must address probabilistic early expiration (XFetch), mutex locking during "
            "cache refill, or dual-cache stale-while-revalidate patterns."
        ),
    },
    "database": {
        "question_text": (
            "Your primary database instance is experiencing connection starvation and thread pool "
            "exhaustion during burst traffic. What architectural strategies and connection pooling "
            "configurations do you implement?"
        ),
        "architectural_constraint": (
            "PostgreSQL max_connections capped at 100 with 500 API worker processes."
        ),
        "evaluation_rubric": (
            "Candidate must propose an external connection pooler (e.g. PgBouncer/Supabase pooler "
            "in transaction mode) and backpressure mechanisms."
        ),
    },
    "security": {
        "question_text": (
            "Untrusted user inputs and third-party webhook payloads are ingested into your "
            "background job pipeline. How do you isolate processing and enforce strict "
            "authorization and data sanitization boundaries?"
        ),
        "architectural_constraint": (
            "Zero arbitrary code execution and strict multi-tenant IDOR isolation."
        ),
        "evaluation_rubric": (
            "Candidate must specify schema validation, cryptographic HMAC signature verification, "
            "parameterized queries, and scoped permissions."
        ),
    },
    "scalability": {
        "question_text": (
            "Your monolithic background task runner is falling behind under exponential queue "
            "ingestion spikes. How do you redesign the worker architecture for horizontal scaling "
            "and graceful degradation?"
        ),
        "architectural_constraint": (
            "Job arrival rate surges to 50,000 jobs/minute with strict 5-second completion SLA."
        ),
        "evaluation_rubric": (
            "Candidate must articulate partitioned queues, dead letter handling, consumer "
            "auto-scaling, and circuit breakers."
        ),
    },
}

_DEFAULT_FALLBACK: Dict[str, str] = {
    "question_text": (
        "Considering the architectural blind spot identified in your previous evaluation, explain "
        "how you would restructure this component to handle failure resilience, monitoring, and "
        "boundary validation under production loads."
    ),
    "architectural_constraint": (
        "Production service must maintain 99.99% uptime with automated error recovery."
    ),
    "evaluation_rubric": (
        "Candidate must demonstrate understanding of error propagation, defensive programming, "
        "and architectural isolation."
    ),
}


def get_fallback_retest_question(category: str, topic: str) -> Dict[str, str]:
    """Retrieve category-specific deterministic fallback re-test question and rubric."""
    clean_cat = category.strip().lower()
    return _CATEGORY_FALLBACKS.get(clean_cat, _DEFAULT_FALLBACK)


def evaluate_retest_fallback(
    candidate_response: str,
    category: str,
    topic: str,
) -> Dict[str, Any]:
    """Heuristic offline evaluation of candidate re-test response when LLM is unavailable."""
    clean_text = candidate_response.strip()
    words = clean_text.split()
    word_count = len(words)

    architecture_keywords = [
        "lock", "mutex", "optimistic", "pessimistic", "cache", "redis",
        "pool", "queue", "partition", "idempotent", "retry", "backoff",
        "circuit breaker", "timeout", "index", "transaction", "isolation",
        "metric", "telemetry", "sanitize", "jwt", "token", "async", "buffer",
        "concurrency", "thread", "connection", "rate limit", "scale",
    ]

    matched_keywords = [
        kw for kw in architecture_keywords
        if re.search(r"\b" + re.escape(kw) + r"\b", clean_text, re.IGNORECASE)
    ]

    score = 45.0
    if word_count >= 30:
        score += 15.0
    if word_count >= 80:
        score += 10.0
    score += min(25.0, len(matched_keywords) * 4.0)

    score = round(max(0.0, min(100.0, score)), 1)
    passed = score >= 70.0 and word_count >= 30

    key_improvements: List[str] = []
    remaining_gaps: List[str] = []

    if matched_keywords:
        key_improvements.append(
            f"Demonstrated awareness of key mechanisms: {', '.join(matched_keywords[:4])}"
        )
    if word_count >= 80:
        key_improvements.append("Provided detailed architectural reasoning and context")

    if not passed:
        remaining_gaps.append(
            "Needs more concrete technical detail on handling boundary conditions and failure modes"
        )
        remaining_gaps.append("Discuss specific architectural tradeoffs and operational metrics")

    feedback = (
        f"Solid architectural defense demonstrating clear mastery of {topic} under the constraints."
        if passed
        else (
            f"Response shows initial intuition regarding {topic}, but lacks technical depth "
            "and mitigation strategies required to pass production re-testing."
        )
    )

    return {
        "score": score,
        "passed": passed,
        "feedback": feedback,
        "key_improvements": key_improvements or ["Identified relevant system components"],
        "remaining_gaps": remaining_gaps,
    }
