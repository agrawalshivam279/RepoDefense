"""Engine for verifying resume technical claims against repository AST and vector evidence."""

import asyncio
import json
import os
import uuid
from typing import Any, List, Optional, Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.prompts import (  # noqa: E402
    CLAIM_VERIFICATION_SYSTEM_PROMPT,
    format_claim_verification_user_prompt,
)
from app.analyzers.embeddings import retrieve_relevant_chunks  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models.analysis import Dependency, Evidence  # noqa: E402
from app.schemas.claim import TechnicalClaim  # noqa: E402
from app.schemas.claim_verification import (  # noqa: E402
    BatchClaimVerificationResponse,
    ClaimVerificationResult,
    EvidenceCitation,
    VerificationStatus,
)
from app.schemas.embedding import RetrievalQuery, RetrievedChunk  # noqa: E402

logger = structlog.get_logger(__name__)


def _build_fallback_verification(
    claim: TechnicalClaim,
    chunks: Sequence[RetrievedChunk],
    evidence_items: Sequence[Evidence],
    dependencies: Sequence[Dependency],
) -> ClaimVerificationResult:
    """Builds deterministic verification result when LiteLLM is unavailable."""
    citations: List[EvidenceCitation] = []
    dep_names = {d.name.lower() for d in dependencies if hasattr(d, "name")}
    claimed_techs = [t.lower() for t in claim.technologies]

    contradiction = False
    if "graphql" in claimed_techs and not any("graphql" in d for d in dep_names):
        if any("rest" in getattr(e, "description", "").lower() for e in evidence_items):
            contradiction = True

    for chunk in chunks[:3]:
        citations.append(
            EvidenceCitation(
                file_path=chunk.file_path,
                symbol_name=f"symbol-{chunk.symbol_id}" if chunk.symbol_id else None,
                snippet=chunk.chunk_content[:250].strip(),
                relevance_score=chunk.similarity,
                source_type="code_chunk",
            )
        )

    if contradiction:
        status = VerificationStatus.CONTRADICTED
        confidence = 0.75
        tech_list = ", ".join(claim.technologies)
        reason = f"Codebase dependencies and architecture contradict claimed use of {tech_list}."
    elif chunks and chunks[0].similarity >= 0.55:
        status = VerificationStatus.SUPPORTED
        confidence = round(min(0.95, max(0.70, chunks[0].similarity + 0.15)), 2)
        reason = (
            f"Found matching code implementations in {chunks[0].file_path} supporting the claim."
        )
    elif any(any(t in d for d in dep_names) for t in claimed_techs):
        status = VerificationStatus.SUPPORTED
        confidence = 0.70
        matched = [t for t in claim.technologies if t.lower() in dep_names]
        reason = (
            f"Claimed technologies ({', '.join(matched)}) verified in repository manifests."
        )
    else:
        status = VerificationStatus.UNVERIFIABLE
        confidence = 0.55
        reason = "Insufficient code chunks or manifest evidence found in cloned snapshot."

    questions = [
        f"In your claim regarding '{claim.statement[:50]}', what trade-offs did you encounter?",
        "How would you re-architect your solution if load scaled by 10x?",
    ]

    return ClaimVerificationResult(
        claim_id=claim.id,
        statement=claim.statement,
        status=status,
        confidence_score=confidence,
        reasoning=reason,
        citations=citations,
        suggested_defense_questions=questions,
    )


async def _call_llm_for_verification(
    user_prompt: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Optional[str]:
    """Invokes LiteLLM to verify a claim against provided code context."""
    effective_key = api_key if api_key is not None else settings.FREELLMAPI_API_KEY
    if not effective_key:
        logger.info("llm_api_key_not_configured_skipping_llm")
        return None

    effective_model = model or settings.LLM_MODEL
    effective_base = base_url or settings.FREELLMAPI_BASE_URL
    timeout = settings.LLM_TIMEOUT_SECONDS

    kwargs: dict[str, Any] = {
        "model": effective_model,
        "messages": [
            {"role": "system", "content": CLAIM_VERIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "timeout": timeout,
        "api_key": effective_key,
    }
    if effective_base:
        kwargs["api_base"] = effective_base

    try:
        response = await litellm.acompletion(**kwargs)
        raw_text = response.choices[0].message.content or ""
        return clean_json_response(raw_text)
    except Exception as exc:
        logger.warning("claim_verification_llm_call_failed", error=str(exc))
        return None


async def verify_single_claim(
    session: AsyncSession,
    project_id: uuid.UUID,
    claim: TechnicalClaim,
    top_k: int = 5,
    min_similarity: float = 0.40,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ClaimVerificationResult:
    """Verifies a single technical claim against repository chunks, evidence, and dependencies."""
    query = RetrievalQuery(
        project_id=project_id,
        query=f"{claim.statement} {' '.join(claim.technologies)}",
        top_k=top_k,
    )
    raw_chunks = await retrieve_relevant_chunks(session, query)
    chunks = [c for c in raw_chunks if c.similarity >= min_similarity]

    evidence_items: List[Evidence] = []
    dependencies: List[Dependency] = []
    try:
        ev_stmt = select(Evidence).where(Evidence.project_id == project_id).limit(10)
        ev_res = await session.execute(ev_stmt)
        if hasattr(ev_res, "scalars"):
            sc = ev_res.scalars()
            if hasattr(sc, "all") and not asyncio.iscoroutine(sc):
                items = sc.all()
                evidence_items = list(items) if not asyncio.iscoroutine(items) else []
    except Exception:
        pass

    try:
        dep_stmt = select(Dependency).where(Dependency.project_id == project_id).limit(50)
        dep_res = await session.execute(dep_stmt)
        if hasattr(dep_res, "scalars"):
            sc = dep_res.scalars()
            if hasattr(sc, "all") and not asyncio.iscoroutine(sc):
                items = sc.all()
                dependencies = list(items) if not asyncio.iscoroutine(items) else []
    except Exception:
        pass

    chunk_dicts = [
        {"file_path": c.file_path, "similarity": c.similarity, "chunk_content": c.chunk_content}
        for c in chunks
    ]
    ev_dicts = [
        {
            "evidence_type": getattr(e, "evidence_type", ""),
            "title": getattr(e, "title", ""),
            "description": getattr(e, "description", ""),
            "file_path": getattr(e, "file_path", ""),
        }
        for e in evidence_items
    ]
    dep_names = [getattr(d, "name", "") for d in dependencies if getattr(d, "name", "")]

    user_prompt = format_claim_verification_user_prompt(
        claim_id=claim.id,
        statement=claim.statement,
        category=claim.category.value if hasattr(claim.category, "value") else str(claim.category),
        technologies=claim.technologies,
        chunks=chunk_dicts,
        evidence_items=ev_dicts,
        dependencies=dep_names,
    )

    cleaned = await _call_llm_for_verification(
        user_prompt, model=model, api_key=api_key, base_url=base_url
    )
    if cleaned:
        try:
            data = json.loads(cleaned)
            result = ClaimVerificationResult.model_validate(data)
            logger.info("verified_claim_via_llm", claim_id=claim.id, status=result.status)
            return result
        except Exception as exc:
            logger.warning("failed_to_parse_llm_verification_json", error=str(exc))

    return _build_fallback_verification(claim, chunks, evidence_items, dependencies)


async def verify_claims_batch(
    session: AsyncSession,
    project_id: uuid.UUID,
    claims: Sequence[TechnicalClaim],
    top_k: int = 5,
    min_similarity: float = 0.40,
) -> BatchClaimVerificationResponse:
    """Evaluates a batch of technical claims and aggregates summary counts."""
    results: List[ClaimVerificationResult] = []
    summary_counts: dict[str, int] = {
        VerificationStatus.SUPPORTED.value: 0,
        VerificationStatus.CONTRADICTED.value: 0,
        VerificationStatus.UNVERIFIABLE.value: 0,
    }

    for claim in claims:
        res = await verify_single_claim(
            session=session,
            project_id=project_id,
            claim=claim,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        results.append(res)
        summary_counts[res.status.value] = summary_counts.get(res.status.value, 0) + 1

    return BatchClaimVerificationResponse(
        project_id=project_id,
        total_claims=len(results),
        verified_claims=results,
        summary_counts=summary_counts,
    )
