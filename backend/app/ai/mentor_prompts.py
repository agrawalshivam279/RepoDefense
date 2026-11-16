"""Prompts and deterministic topic synthesis for Mentor Mode teaching content."""

import html
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.schemas.mentor import (
    CodeRemediationSnippet,
    MentorExplanationResponse,
)

MENTOR_SYSTEM_PROMPT = (
    "You are a Principal Software Engineer and Master Architectural Mentor at RepoDefense.\n"
    "Your goal is to educate, elevate, and mentor an engineer on a critical design gap.\n"
    "Principles:\n"
    "1. Root Cause: Clearly explain the underlying architectural failure mode or bottleneck.\n"
    "2. Core Principle: Teach the production engineering pattern that resolves it.\n"
    "3. Drop-in Remediation: Provide concrete Before-and-After code showing the anti-pattern "
    "transformed into robust production code.\n"
    "4. Key Takeaways: Provide 2-4 concise, high-impact architectural rules.\n"
    "5. Socratic Follow-Up: Pose a thought-provoking challenge question preparing for re-testing.\n"
    "6. Output Format: Output strictly a single JSON object conforming to the schema without "
    "markdown fences.\n\n"
    "Schema:\n"
    "{\n"
    '  "category": "<str>",\n'
    '  "topic": "<str>",\n'
    '  "architectural_risk": "<str>",\n'
    '  "core_concept": "<str>",\n'
    '  "mentor_advice": "<str>",\n'
    '  "code_examples": [\n'
    "    {\n"
    '      "title": "<str>",\n'
    '      "language": "<str>",\n'
    '      "file_context": "<str>",\n'
    '      "before_code": "<str>",\n'
    '      "after_code": "<str>",\n'
    '      "explanation": "<str>"\n'
    "    }\n"
    "  ],\n"
    '  "key_takeaways": ["<str>"],\n'
    '  "socratic_followup": "<str>"\n'
    "}"
)


def sanitize_xml(text: Optional[str], max_chars: int = 4000) -> str:
    """Sanitize and truncate untrusted user input before embedding in prompt."""
    if not text:
        return ""
    truncated = text.strip()[:max_chars]
    return html.escape(truncated, quote=True)


def build_mentor_user_prompt(
    category: str,
    topic: str,
    question_prompt: Optional[str],
    candidate_response: Optional[str],
    feedback: Optional[str],
    code_context: Optional[str],
    language: str,
) -> str:
    """Format prompt with XML delimiters to isolate untrusted input."""
    clean_cat = sanitize_xml(category)
    clean_topic = sanitize_xml(topic)
    clean_lang = sanitize_xml(language)
    clean_q = sanitize_xml(question_prompt)
    clean_resp = sanitize_xml(candidate_response)
    clean_fb = sanitize_xml(feedback)
    clean_code = sanitize_xml(code_context)

    return (
        f'<weakness_context category="{clean_cat}" topic="{clean_topic}" language="{clean_lang}">\n'
        f"<question_prompt>\n{clean_q}\n</question_prompt>\n"
        f"<candidate_response>\n{clean_resp}\n</candidate_response>\n"
        f"<evaluator_feedback>\n{clean_fb}\n</evaluator_feedback>\n"
        f"<code_context>\n{clean_code}\n</code_context>\n"
        "</weakness_context>\n\n"
        "Synthesize an architectural mentor teaching explanation with code remediation."
    )


def build_deterministic_mentor_explanation(
    category: str,
    topic: str,
    language: str = "python",
    feedback: Optional[str] = None,
) -> MentorExplanationResponse:
    """Generate high-quality deterministic educational content when LLM is unavailable."""
    norm_topic = topic.lower()

    if any(k in norm_topic for k in ["pool", "connection", "starvation", "db", "database"]):
        risk = (
            "Unbounded database session creation without connection pooling exhausts "
            "database sockets under high load."
        )
        concept = "Scoped Session Lifecycle & Asynchronous Connection Pooling"
        advice = (
            "Borrow database connections from a bounded pool and release them deterministically."
        )
        before = (
            "# Vulnerable: creates a raw unpooled connection per request\n"
            "def get_user_data(user_id: str):\n"
            "    conn = psycopg2.connect(DATABASE_URL)\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n"
            "    return cursor.fetchone()"
        )
        after = (
            "# Production: Async pooled engine with deterministic context management\n"
            "async def get_user_data(user_id: UUID, session: AsyncSession) -> Optional[User]:\n"
            "    stmt = select(User).where(User.id == user_id)\n"
            "    result = await session.execute(stmt)\n"
            "    return result.scalar_one_or_none()"
        )
        explanation = (
            "Connection pooling eliminates socket exhaustion and reduces handshake latency."
        )
        file_ctx = "backend/app/core/database.py"
        followup = (
            "How would you configure pool pre-ping and max overflow to handle transient failovers?"
        )
    elif any(k in norm_topic for k in ["race", "concurren", "atomic", "lock", "conflict"]):
        risk = (
            "Read-modify-write sequences executed concurrently lead to lost updates and "
            "silent state corruption."
        )
        concept = "Optimistic Concurrency Control (OCC) & Row-Level Locking"
        advice = (
            "Protect shared mutations with version numbers or atomic database expressions."
        )
        before = (
            "# Vulnerable: Lost update race condition\n"
            "async def increment_counter(item_id: UUID, session: AsyncSession):\n"
            "    item = await session.get(Item, item_id)\n"
            "    item.count += 1\n"
            "    await session.commit()"
        )
        after = (
            "# Hardened: Atomic database-level increment or row lock\n"
            "async def increment_counter(item_id: UUID, session: AsyncSession):\n"
            "    stmt = update(Item).where(Item.id == item_id).values(count=Item.count + 1)\n"
            "    await session.execute(stmt)\n"
            "    await session.commit()"
        )
        explanation = (
            "Delegating atomicity to the database engine prevents interleaving race windows."
        )
        file_ctx = "backend/app/services/counter.py"
        followup = (
            "What are the tradeoffs between pessimistic locking and optimistic locking?"
        )
    elif any(k in norm_topic for k in ["cache", "redis", "invalidation", "stampede"]):
        risk = (
            "Cache stampedes on TTL expiry can trigger cascading database outages when "
            "concurrent workers query simultaneously."
        )
        concept = "Cache-Aside with Probabilistic Early Expiration & Distributed Mutex"
        advice = (
            "Combine short TTLs with background asynchronous pre-fetching or a distributed mutex."
        )
        before = (
            "# Vulnerable: Standard cache miss triggers thundering herd\n"
            "async def get_cached(key: str):\n"
            "    val = await redis.get(key)\n"
            "    if not val:\n"
            "        val = await query_heavy_db()\n"
            "        await redis.set(key, val, ex=60)\n"
            "    return val"
        )
        after = (
            "# Hardened: Distributed lock on cache miss with fallback\n"
            "async def get_cached(key: str):\n"
            "    val = await redis.get(key)\n"
            "    if val is not None:\n"
            "        return val\n"
            "    async with redis.lock(f'lock:{key}', timeout=5):\n"
            "        val = await redis.get(key)  # Double-check\n"
            "        if val is None:\n"
            "            val = await query_heavy_db()\n"
            "            await redis.set(key, val, ex=60)\n"
            "    return val"
        )
        explanation = (
            "A double-checked distributed lock ensures only a single worker executes the DB query."
        )
        file_ctx = "backend/app/services/cache.py"
        followup = "How would you handle cache invalidation when mutations occur across services?"
    elif any(k in norm_topic for k in ["rate_limit", "throttle", "scalab"]):
        risk = "Unrestricted public endpoints invite DDoS and sudden compute exhaustion."
        concept = "Sliding Window Counter / Token Bucket Rate Limiting"
        advice = "Enforce rate limiting at API gateway and application layers with Redis."
        before = (
            "# Vulnerable: Unbounded endpoint without throttling\n"
            "@app.post('/api/v1/auth/login')\n"
            "async def login(req: LoginRequest):\n"
            "    return await authenticate(req)"
        )
        after = (
            "# Hardened: Rate limited per IP and user identity\n"
            "@app.post('/api/v1/auth/login')\n"
            "async def login(req: LoginRequest, limiter: RateLimiter = Depends(get_limiter)):\n"
            "    await limiter.check_rate_limit(req.ip, limit=10, window_seconds=60)\n"
            "    return await authenticate(req)"
        )
        explanation = "Sliding window rate limiters enforce burst tolerances and stop brute-force."
        file_ctx = "backend/app/api/v1/auth.py"
        followup = "What status code and response headers should an API return when rate limited?"
    else:
        risk = f"Suboptimal design patterns in {topic} introduce maintainability debt."
        concept = "Separation of Concerns & Interface-Driven Decoupling"
        advice = feedback or f"Focus on designing clear boundaries around {topic}."
        before = (
            f"# Anti-pattern: Monolithic coupling in {topic}\n"
            "def process_data(payload: dict):\n"
            "    write_to_db(payload)\n"
            "    send_webhook(payload)"
        )
        after = (
            "# Hardened: Domain-driven service decoupling\n"
            "async def process_data(payload: ValidatedSchema, service: DomainService):\n"
            "    await service.execute_workflow(payload)"
        )
        explanation = "Decoupled domain services improve testability and isolate blast radius."
        file_ctx = "backend/app/services/workflow.py"
        followup = f"How would you author integration tests to verify resilience of {topic}?"

    return MentorExplanationResponse(
        explanation_id=uuid.uuid4(),
        category=category,
        topic=topic,
        architectural_risk=risk,
        core_concept=concept,
        mentor_advice=advice,
        code_examples=[
            CodeRemediationSnippet(
                title=f"Hardened Remediation for {topic.replace('_', ' ').title()}",
                language=language,
                file_context=file_ctx,
                before_code=before,
                after_code=after,
                explanation=explanation,
            )
        ],
        key_takeaways=[
            f"Ground all {topic} implementations in production failure models.",
            "Always encapsulate resource lifecycles with deterministic cleanup handlers.",
            "Introduce bounded limits on all unbounded I/O operations.",
        ],
        socratic_followup=followup,
        generated_at=datetime.now(timezone.utc),
    )
