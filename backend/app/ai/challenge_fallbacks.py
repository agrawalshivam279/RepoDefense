"""Deterministic offline fallbacks for Mentor Mode Mini Challenges."""

import uuid
from typing import List

from app.schemas.challenge import (
    ChallengeEvaluationResponse,
    MiniChallengeDifficulty,
    MiniChallengeResponse,
)


def build_fallback_challenge(
    category: str,
    topic: str,
    difficulty: MiniChallengeDifficulty = MiniChallengeDifficulty.INTERMEDIATE,
    language: str = "python",
) -> MiniChallengeResponse:
    """Generate deterministic architectural mini-challenge when LLM is unavailable."""
    norm_topic = topic.lower()

    if "pool" in norm_topic or "connect" in norm_topic:
        title = "Database Connection Starvation Under Concurrency Spike"
        scenario = (
            "During a burst of 5,000 req/sec, PostgreSQL exhausts its max connections, "
            "triggering FATAL: remaining connection slots are reserved. Inspect the worker "
            "code below where raw connections are opened on each request without pooling."
        )
        starter_code = (
            "async def handle_request(payload: dict):\n"
            "    conn = await asyncpg.connect(settings.DATABASE_URL)\n"
            "    try:\n"
            "        await conn.execute('INSERT INTO events VALUES ($1)', payload['data'])\n"
            "    finally:\n"
            "        await conn.close()"
        )
        requirements = [
            "Implement a shared async connection pool with bounded max_size and min_size.",
            "Acquire connections from the pool with an acquisition timeout (e.g. 2.0s).",
            "Gracefully catch PoolTimeout and return a 503 backpressure signal.",
        ]
        hints = [
            "Avoid instantiating asyncpg.connect() inside request handlers.",
            "Use asyncpg.create_pool() during application lifespan initialization.",
            "Always wrap pool.acquire() in an async context manager.",
        ]
    elif "lock" in norm_topic or "race" in norm_topic:
        title = "Concurrency Lost Updates on Shared Balance State"
        scenario = (
            "Concurrent withdrawal requests for the same account read identical balances "
            "before either commits, causing double-spending and lost updates under load."
        )
        starter_code = (
            "async def withdraw(account_id: str, amount: float, db: AsyncSession):\n"
            "    account = await db.get(Account, account_id)\n"
            "    if account.balance >= amount:\n"
            "        account.balance -= amount\n"
            "        await db.commit()\n"
            "        return True\n"
            "    return False"
        )
        requirements = [
            "Use pessimistic row-level locking (SELECT ... FOR UPDATE) or atomic update.",
            "Ensure the check and decrement occur in a single atomic transaction boundary.",
            "Handle lock timeout or deadlock exceptions with retry backoff.",
        ]
        hints = [
            "In SQLAlchemy, pass with_for_update=True to your select query.",
            "Alternatively: UPDATE account SET balance = balance - :amt "
            "WHERE id = :id AND balance >= :amt.",
        ]
    elif "stampede" in norm_topic or "cache" in norm_topic:
        title = "Cache Stampede (Thundering Herd) on High-Velocity Key Expiry"
        scenario = (
            "A popular leaderboard cache key expires at high traffic, triggering 2,000 "
            "concurrent queries simultaneously to recompute the same payload."
        )
        starter_code = (
            "async def get_leaderboard(redis_client, db):\n"
            "    cached = await redis_client.get('leaderboard')\n"
            "    if cached:\n"
            "        return json.loads(cached)\n"
            "    data = await db.compute_expensive_leaderboard()\n"
            "    await redis_client.setex('leaderboard', 60, json.dumps(data))\n"
            "    return data"
        )
        requirements = [
            "Implement distributed mutual exclusion lock (single-flight / mutex).",
            "Have waiting requests await the lock or retry cache read with exponential backoff.",
            "Set cache expiration with probabilistic early recomputation or jitter.",
        ]
        hints = [
            "Use Redis SET key token NX EX 5 to elect a single worker to recompute.",
            "Other requests should briefly sleep and re-check cache before hitting the DB.",
        ]
    else:
        title = f"Architectural Hardening for {topic.replace('_', ' ').title()}"
        scenario = (
            f"The subsystem handling {topic} lacks resilience guarantees under load. "
            "Refactor the architecture to incorporate clear failure boundaries and timeouts."
        )
        starter_code = (
            "# Unprotected implementation\n"
            f"async def process_{topic.lower()}(request_data: dict):\n"
            "    result = await execute_internal_task(request_data)\n"
            "    return result"
        )
        requirements = [
            "Enforce strict timeouts on downstream I/O dependencies.",
            "Isolate state changes within idempotent transaction boundaries.",
            "Provide graceful degradation or fallback when downstream calls fail.",
        ]
        hints = [
            "Consider wrapping remote calls with asyncio.wait_for(..., timeout=5.0).",
            "Ensure resources are released cleanly in finally blocks.",
        ]

    return MiniChallengeResponse(
        category=category,
        topic=topic,
        difficulty=difficulty,
        title=title,
        scenario=scenario,
        starter_code=starter_code,
        language=language,
        requirements=requirements,
        hints=hints,
    )


def build_fallback_evaluation(
    challenge_id: uuid.UUID,
    candidate_solution: str,
    requirements: List[str],
) -> ChallengeEvaluationResponse:
    """Evaluate candidate solution deterministically based on static code heuristics."""
    code_lower = candidate_solution.lower()
    strengths: List[str] = []
    missing: List[str] = []

    if any(k in code_lower for k in ["pool", "create_pool", "acquire"]):
        strengths.append("Implemented bounded connection pool acquisition pattern.")
    if any(k in code_lower for k in ["timeout", "wait_for", "503", "backoff"]):
        strengths.append("Handled timeouts and backpressure to protect downstream systems.")
    if any(k in code_lower for k in ["for_update", "atomic", "lock", "mutex", "nx"]):
        strengths.append("Employed concurrency controls to avoid race conditions.")
    if any(k in code_lower for k in ["try", "except", "finally"]):
        strengths.append("Used structured exception handling for error isolation.")

    if len(strengths) >= 2 and len(candidate_solution.strip()) > 60:
        passed = True
        score = 85.0
        critique = (
            "Strong architectural solution. You correctly recognized the failure mode, "
            "applied appropriate resource boundaries and concurrency synchronization, and "
            "structured the code for operational stability under load."
        )
    else:
        passed = False
        score = 55.0
        missing.append("Ensure full requirement coverage with resource boundaries and timeouts.")
        critique = (
            "The proposed solution is incomplete or superficial. In production, "
            "this implementation does not sufficiently isolate the failure domain."
        )

    model_solution = (
        "# Production Reference Solution\n"
        "async def execute_resiliently(pool, request_data: dict):\n"
        "    try:\n"
        "        async with asyncio.timeout(2.0):\n"
        "            async with pool.acquire() as conn:\n"
        "                async with conn.transaction():\n"
        "                    return await conn.fetchrow('...', request_data)\n"
        "    except (asyncio.TimeoutError, PoolTimeout):\n"
        "        raise HTTPException(status_code=503, detail='Service Under Heavy Load')"
    )

    return ChallengeEvaluationResponse(
        challenge_id=challenge_id,
        passed=passed,
        score=score,
        strengths=strengths,
        missing_elements=missing,
        critique=critique,
        model_solution=model_solution,
    )
