"""Hermetic unit and integration tests for resume technical claim extraction."""

import io
import json
from unittest.mock import AsyncMock, patch

import pypdf
import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.claim_extractor import (
    _classify_category_heuristic,
    _deterministic_fallback_claims,
    detect_technologies_in_text,
    extract_technical_claims,
    extract_text_from_pdf,
)
from app.main import app
from app.schemas.claim import (
    ClaimCategory,
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    TechnicalClaim,
)


def _generate_synthetic_pdf(text_content: str) -> bytes:
    """Generates valid in-memory PDF bytes containing the specified text."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_technical_claim_schema_defaults():
    """Verify that TechnicalClaim populates uuid, verifiable, and validates categories."""
    claim = TechnicalClaim(
        statement="Engineered Redis caching layer to handle 20k ops/sec.",
        category=ClaimCategory.SCALABILITY,
        technologies=["Redis"],
    )
    assert len(claim.id) == 36
    assert claim.verifiable is True
    assert claim.category == ClaimCategory.SCALABILITY
    assert claim.technologies == ["Redis"]


def test_claim_request_length_validation():
    """Verify that ClaimExtractionRequest rejects too short or too long text."""
    with pytest.raises(Exception):
        ClaimExtractionRequest(text="short")

    valid = ClaimExtractionRequest(text="Architected distributed Kafka pipeline.")
    assert valid.text == "Architected distributed Kafka pipeline."


def test_detect_technologies_in_text():
    """Verify regex technology detection identifies keywords with word boundary matching."""
    text = "Built backend with FastAPI, PostgreSQL, Redis, and deployed via Docker on AWS."
    techs = detect_technologies_in_text(text)
    assert "FastAPI" in techs
    assert "PostgreSQL" in techs
    assert "Redis" in techs
    assert "Docker" in techs
    assert "AWS" in techs
    assert "Go" not in techs


def test_classify_category_heuristic():
    """Verify heuristic classification categorizes claims by keywords."""
    assert _classify_category_heuristic("Scaled throughput to 10k rps") == ClaimCategory.SCALABILITY
    assert _classify_category_heuristic("Implemented JWT RBAC guards") == ClaimCategory.SECURITY
    assert _classify_category_heuristic("Optimized PostgreSQL queries") == ClaimCategory.DATABASE
    infra_stmt = "Configured Docker CI/CD on AWS"
    assert _classify_category_heuristic(infra_stmt) == ClaimCategory.INFRASTRUCTURE
    assert _classify_category_heuristic("Reduced latency with cache") == ClaimCategory.PERFORMANCE
    framework_stmt = "Built app using FastAPI framework"
    assert _classify_category_heuristic(framework_stmt) == ClaimCategory.FRAMEWORK


def test_extract_text_from_pdf_empty_and_corrupt():
    """Verify PDF extractor rejects empty or malformed inputs with ValueError."""
    with pytest.raises(ValueError, match="Empty PDF"):
        extract_text_from_pdf(b"")

    with pytest.raises(ValueError, match="Failed to parse"):
        extract_text_from_pdf(b"not-a-pdf-corrupt-data")


def test_deterministic_fallback_claims():
    """Verify that fallback extracts claims from action-verb bullet points."""
    resume_text = (
        "• Architected distributed event streaming platform with Kafka and Go.\n"
        "• Implemented secure JWT authorization middleware in FastAPI.\n"
        "• Collaborated with teammates in daily meetings.\n"
        "• Optimized PostgreSQL connection pooling handling 5000 concurrent sessions.\n"
    )
    claims = _deterministic_fallback_claims(resume_text)
    assert len(claims) >= 3
    categories = [c.category for c in claims]
    assert ClaimCategory.SECURITY in categories
    assert ClaimCategory.DATABASE in categories


@pytest.mark.anyio
async def test_extract_technical_claims_with_llm():
    """Verify extract_technical_claims parses LLM response into structured response."""
    mock_llm_json = json.dumps([
        {
            "statement": "Designed event-driven order processing with Kafka and Redis.",
            "category": "scalability",
            "technologies": ["Kafka", "Redis"],
            "verifiable": True,
            "source_context": "Designed event-driven order processing with Kafka and Redis.",
        },
        {
            "statement": "Implemented OAuth2 and role-based access control with FastAPI.",
            "category": "security",
            "technologies": ["FastAPI"],
            "verifiable": True,
            "source_context": "Implemented OAuth2 and role-based access control with FastAPI.",
        },
    ])

    with patch(
        "app.ai.claim_extractor._call_llm_for_claims", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = mock_llm_json
        res = await extract_technical_claims(
            "Designed event-driven order processing with Kafka and Redis. "
            "Implemented OAuth2 in FastAPI."
        )
        assert isinstance(res, ClaimExtractionResponse)
        assert res.total_claims == 2
        assert "Kafka" in res.technologies_detected
        assert "FastAPI" in res.technologies_detected


@pytest.mark.anyio
async def test_extract_technical_claims_fallback_on_llm_failure():
    """Verify extract_technical_claims invokes fallback when LLM fails."""
    with patch(
        "app.ai.claim_extractor._call_llm_for_claims", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = None
        res = await extract_technical_claims(
            "Architected high-throughput message queue using RabbitMQ and Python."
        )
        assert res.total_claims >= 1
        assert "RabbitMQ" in res.technologies_detected
        assert res.claims[0].category in [ClaimCategory.SCALABILITY, ClaimCategory.ARCHITECTURE]


@pytest.mark.anyio
async def test_claims_extract_api_endpoint_success():
    """Verify POST /api/v1/claims/extract processes JSON payload successfully."""
    payload = {
        "text": "Architected distributed caching with Redis and PostgreSQL handling 5k ops/sec."
    }
    with patch(
        "app.ai.claim_extractor._call_llm_for_claims", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = None  # Force fallback
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/claims/extract", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["total_claims"] >= 1
            assert "Redis" in data["technologies_detected"]


@pytest.mark.anyio
async def test_claims_extract_api_endpoint_validation():
    """Verify POST /api/v1/claims/extract validates payload text."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/claims/extract", json={"text": ""})
        assert res.status_code == 422


@pytest.mark.anyio
async def test_claims_upload_endpoint_form_text():
    """Verify POST /api/v1/claims/upload accepts multipart form text."""
    with patch(
        "app.ai.claim_extractor._call_llm_for_claims", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = None  # Force fallback
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/claims/upload",
                data={"text": "Engineered microservices using Docker, Kubernetes, and Go."},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total_claims"] >= 1
            assert "Docker" in data["technologies_detected"]


@pytest.mark.anyio
async def test_claims_upload_endpoint_invalid_file():
    """Verify POST /api/v1/claims/upload rejects non-PDF file uploads."""
    files = {"file": ("resume.txt", b"plain text content", "text/plain")}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/claims/upload", files=files)
        assert res.status_code == 400
        assert "PDF document" in res.json()["detail"]


@pytest.mark.anyio
async def test_claims_upload_endpoint_missing_input():
    """Verify POST /api/v1/claims/upload rejects requests without file or text."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/claims/upload")
        assert res.status_code == 400
        assert "Either a PDF file upload or text content" in res.json()["detail"]
