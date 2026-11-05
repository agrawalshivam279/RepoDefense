"""Hermetic unit and integration tests for technical claim verification."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.claim_verifier import (
    _build_fallback_verification,
    verify_claims_batch,
    verify_single_claim,
)
from app.ai.prompts import format_claim_verification_user_prompt
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.analysis import Dependency, Evidence
from app.models.project import Project, User
from app.schemas.claim import ClaimCategory, TechnicalClaim
from app.schemas.claim_verification import (
    BatchClaimVerificationResponse,
    ClaimVerificationResult,
    EvidenceCitation,
    VerificationStatus,
)
from app.schemas.embedding import RetrievedChunk


def test_claim_verification_schemas():
    """Verify serialization and validation of claim verification schemas."""
    citation = EvidenceCitation(
        file_path="app/core/database.py",
        start_line=10,
        end_line=35,
        snippet="class DatabaseEngine: ...",
        relevance_score=0.88,
    )
    result = ClaimVerificationResult(
        claim_id="claim-1",
        statement="Engineered async SQLAlchemy pool",
        status=VerificationStatus.SUPPORTED,
        confidence_score=0.92,
        reasoning="Found DatabaseEngine in app/core/database.py",
        citations=[citation],
        suggested_defense_questions=["How does the pool handle exhaustion?"],
    )
    assert result.status == VerificationStatus.SUPPORTED
    assert len(result.citations) == 1
    assert result.citations[0].relevance_score == 0.88

    batch = BatchClaimVerificationResponse(
        project_id=uuid.uuid4(),
        total_claims=1,
        verified_claims=[result],
        summary_counts={"supported": 1, "contradicted": 0, "unverifiable": 0},
    )
    assert batch.total_claims == 1
    assert batch.summary_counts["supported"] == 1


def test_prompt_formatting_xml_delimiters():
    """Verify XML context isolation and escaping for claim verification prompt."""
    prompt = format_claim_verification_user_prompt(
        claim_id="c-123",
        statement="Implemented Redis caching <spike>",
        category="scalability",
        technologies=["Redis", "FastAPI"],
        chunks=[{
            "file_path": "cache.py", "similarity": 0.82, "chunk_content": "def get(): pass"
        }],
        evidence_items=[{
            "evidence_type": "cache", "title": "R", "description": "KV", "file_path": "c.py"
        }],
        dependencies=["redis>=5.0", "fastapi>=0.110"],
    )
    assert '<claim id="c-123" category="scalability">' in prompt
    assert "<statement>Implemented Redis caching &lt;spike&gt;</statement>" in prompt
    assert "<codebase_evidence>" in prompt
    assert '<code_chunk file="cache.py" similarity="0.82">' in prompt


def test_deterministic_fallback_supported_and_contradicted():
    """Verify fallback accurately classifies supported, contradicted, and unverifiable states."""
    claim = TechnicalClaim(
        id="c-1",
        statement="Architected Redis distributed cache",
        category=ClaimCategory.SCALABILITY,
        technologies=["Redis"],
    )
    chunk = RetrievedChunk(
        id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        file_path="app/cache.py",
        symbol_id=None,
        chunk_content="class RedisCacheManager: ...",
        similarity=0.85,
        token_count=50,
    )
    dep = Dependency(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="redis",
        version="5.0.1",
        source_file="pyproject.toml",
    )
    res_sup = _build_fallback_verification(claim, [chunk], [], [dep])
    assert res_sup.status == VerificationStatus.SUPPORTED
    assert res_sup.confidence_score >= 0.70

    contra_claim = TechnicalClaim(
        id="c-2",
        statement="Implemented GraphQL federation gateway",
        category=ClaimCategory.ARCHITECTURE,
        technologies=["GraphQL"],
    )
    ev_rest = Evidence(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        evidence_type="endpoint",
        title="REST Router",
        description="FastAPI REST endpoints",
        file_path="app/main.py",
        start_line=1,
        end_line=20,
    )
    res_contra = _build_fallback_verification(contra_claim, [], [ev_rest], [dep])
    assert res_contra.status == VerificationStatus.CONTRADICTED

    res_unverif = _build_fallback_verification(contra_claim, [], [], [dep])
    assert res_unverif.status == VerificationStatus.UNVERIFIABLE


@pytest.mark.anyio
async def test_verify_single_claim_via_llm_success():
    """Verify single claim verification succeeds with mocked LiteLLM output."""
    mock_session = AsyncMock()
    mock_db_res = MagicMock()
    mock_db_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_db_res

    mock_chunks = [
        RetrievedChunk(
            id=uuid.uuid4(),
            file_id=uuid.uuid4(),
            file_path="app/security.py",
            symbol_id=None,
            chunk_content="def verify_jwt_token(): pass",
            similarity=0.88,
            token_count=40,
        )
    ]
    claim = TechnicalClaim(
        id="c-3",
        statement="Implemented JWT authentication",
        category=ClaimCategory.SECURITY,
        technologies=["JWT"],
    )

    llm_payload = {
        "claim_id": "c-3",
        "statement": "Implemented JWT authentication",
        "status": "supported",
        "confidence_score": 0.95,
        "reasoning": "Code in app/security.py implements JWT validation.",
        "citations": [{
            "file_path": "app/security.py", "start_line": 15, "end_line": 30,
            "snippet": "def verify_jwt_token(): pass", "relevance_score": 0.88,
            "source_type": "code_chunk",
        }],
        "suggested_defense_questions": ["Revocation?"],
    }

    chunks_mock = AsyncMock(return_value=mock_chunks)
    llm_mock = AsyncMock(return_value=json.dumps(llm_payload))

    with patch("app.ai.claim_verifier.retrieve_relevant_chunks", chunks_mock), \
         patch("app.ai.claim_verifier._call_llm_for_verification", llm_mock):
        res = await verify_single_claim(
            session=mock_session,
            project_id=uuid.uuid4(),
            claim=claim,
            api_key="sk-test-key",
        )
        assert res.status == VerificationStatus.SUPPORTED
        assert res.confidence_score == 0.95
        assert len(res.citations) == 1


@pytest.mark.anyio
async def test_verify_claims_batch():
    """Verify batch verification aggregates claims and builds summary counts."""
    mock_session = AsyncMock()
    claims = [
        TechnicalClaim(id="c-1", statement="Redis cache", category=ClaimCategory.SCALABILITY),
        TechnicalClaim(id="c-2", statement="Postgres DB", category=ClaimCategory.DATABASE),
    ]

    r1 = ClaimVerificationResult(
        claim_id="c-1", statement="Redis cache", status=VerificationStatus.SUPPORTED,
        confidence_score=0.8, reasoning="ok",
    )
    r2 = ClaimVerificationResult(
        claim_id="c-2", statement="Postgres DB", status=VerificationStatus.UNVERIFIABLE,
        confidence_score=0.5, reasoning="none",
    )

    with patch("app.ai.claim_verifier.verify_single_claim", AsyncMock(side_effect=[r1, r2])):
        batch = await verify_claims_batch(
            session=mock_session, project_id=uuid.uuid4(), claims=claims
        )
        assert batch.total_claims == 2
        assert batch.summary_counts["supported"] == 1
        assert batch.summary_counts["unverifiable"] == 1


@pytest.mark.anyio
async def test_api_verify_claims_unauthenticated():
    """Verify endpoint rejects unauthenticated request with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/projects/{uuid.uuid4()}/claims/verify", json={"claims": []}
        )
        assert res.status_code == 401


@pytest.mark.anyio
async def test_api_verify_claims_success():
    """Verify endpoint processes verification request and returns batch result."""
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    mock_user = User(id=user_id, email="dev@repodefense.dev")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_project = Project(
        id=proj_id, user_id=user_id, name="repodefense-test",
        github_url="https://github.com/test/repo", status="analyzed",
    )
    mock_db = AsyncMock()
    proj_result = MagicMock()
    proj_result.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = proj_result
    app.dependency_overrides[get_db] = lambda: mock_db

    claim_item = {
        "id": "c-100", "statement": "FastAPI gateway", "category": "architecture",
        "technologies": ["FastAPI"], "verifiable": True,
    }
    dummy_batch = BatchClaimVerificationResponse(
        project_id=proj_id, total_claims=1,
        verified_claims=[
            ClaimVerificationResult(
                claim_id="c-100", statement="FastAPI gateway",
                status=VerificationStatus.SUPPORTED, confidence_score=0.9,
                reasoning="FastAPI found in repo",
            )
        ],
        summary_counts={"supported": 1},
    )

    try:
        with patch("app.api.v1.claims.verify_claims_batch", AsyncMock(return_value=dummy_batch)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                headers = {"Authorization": "Bearer test-jwt"}
                payload = {"claims": [claim_item], "top_k_chunks": 5}

                url1 = f"/api/v1/projects/{proj_id}/claims/verify"
                res1 = await ac.post(url1, json=payload, headers=headers)
                assert res1.status_code == 200
                data = res1.json()
                assert data["total_claims"] == 1
                assert data["verified_claims"][0]["status"] == "supported"

                url2 = f"/api/v1/claims/verify/{proj_id}"
                res2 = await ac.post(url2, json=payload, headers=headers)
                assert res2.status_code == 200
    finally:
        app.dependency_overrides.clear()
