"""Resume text extraction and AI-driven technical claim extraction engine."""

import io
import json
import os
import re
from typing import Any

import pypdf
import structlog

# Ensure LiteLLM does not attempt to download cost maps or send telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm  # noqa: E402

litellm.telemetry = False
litellm.drop_params = True

from app.ai.llm import clean_json_response  # noqa: E402
from app.ai.prompts import (  # noqa: E402
    CLAIM_EXTRACTION_SYSTEM_PROMPT,
    format_claim_extraction_user_prompt,
)
from app.core.config import settings  # noqa: E402
from app.schemas.claim import (  # noqa: E402
    ClaimCategory,
    ClaimExtractionResponse,
    TechnicalClaim,
)

logger = structlog.get_logger(__name__)

# Canonical keywords for static technology detection
KNOWN_TECH_CATALOG = [
    "Python", "FastAPI", "Django", "Flask", "TypeScript", "JavaScript",
    "React", "Next.js", "Node.js", "Express", "PostgreSQL", "MySQL",
    "MongoDB", "Redis", "Kafka", "RabbitMQ", "Docker", "Kubernetes",
    "AWS", "GCP", "Azure", "GraphQL", "REST", "gRPC", "CI/CD",
    "GitHub Actions", "Tree-sitter", "pgvector", "SQLAlchemy", "ARQ",
    "Celery", "Elasticsearch", "Nginx", "Linux", "Terraform", "Go",
    "Rust", "Java", "Spring Boot", "C++", "PyTorch", "TensorFlow",
]

_ACTION_VERB_REGEX = re.compile(
    r"\b(architected|designed|implemented|built|developed|scaled|"
    r"optimized|configured|refactored|deployed|migrated|integrated|engineered)\b",
    re.IGNORECASE,
)


def extract_text_from_pdf(file_bytes: bytes, max_pages: int = 15) -> str:
    """Extracts raw text from PDF bytes statically using pypdf without code execution."""
    if not file_bytes:
        raise ValueError("Empty PDF file payload.")

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        if len(reader.pages) == 0:
            raise ValueError("PDF document contains no pages.")

        extracted_text: list[str] = []
        for page in reader.pages[:max_pages]:
            text = page.extract_text()
            if text:
                extracted_text.append(text.strip())

        full_text = "\n\n".join(extracted_text).strip()
        if not full_text:
            raise ValueError("No extractable text found in PDF document.")

        return full_text
    except Exception as exc:
        logger.warning("pdf_extraction_failed", error=str(exc))
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Failed to parse PDF document: {exc}") from exc


def detect_technologies_in_text(text: str) -> list[str]:
    """Detects and deduplicates known technologies cited in text."""
    found: set[str] = set()
    text_lower = text.lower()
    for tech in KNOWN_TECH_CATALOG:
        pattern = rf"\b{re.escape(tech.lower())}\b"
        if re.search(pattern, text_lower):
            found.add(tech)
    return sorted(found)


def _classify_category_heuristic(statement: str) -> ClaimCategory:
    """Classifies a claim into a ClaimCategory based on keyword heuristics."""
    stmt = statement.lower()
    security_keys = [
        "auth", "jwt", "rbac", "encrypt", "token", "oauth", "security", "permission",
    ]
    if any(k in stmt for k in security_keys):
        return ClaimCategory.SECURITY
    scale_keys = [
        "scale", "throughput", "concurren", "spike", "rps", "ops/sec", "req/sec", "load",
    ]
    if any(k in stmt for k in scale_keys):
        return ClaimCategory.SCALABILITY
    if any(k in stmt for k in ["sql", "postgres", "redis", "database", "query", "orm", "index"]):
        return ClaimCategory.DATABASE
    if any(k in stmt for k in ["docker", "k8s", "kubernetes", "ci/cd", "aws", "deploy", "infra"]):
        return ClaimCategory.INFRASTRUCTURE
    if any(k in stmt for k in ["latency", "cache", "profil", "optimiz", "memory", "speed"]):
        return ClaimCategory.PERFORMANCE
    if any(k in stmt for k in ["fastapi", "react", "next.js", "django", "express", "framework"]):
        return ClaimCategory.FRAMEWORK
    return ClaimCategory.ARCHITECTURE


def _deterministic_fallback_claims(text: str) -> list[TechnicalClaim]:
    """Generates structured claims using deterministic regex heuristics when LLM is unavailable."""
    claims: list[TechnicalClaim] = []
    lines = [line.strip() for line in re.split(r"[\r\n•\-\*]+", text) if line.strip()]

    for line in lines:
        if len(line) < 20 or len(line) > 300:
            continue
        if _ACTION_VERB_REGEX.search(line):
            techs = detect_technologies_in_text(line)
            category = _classify_category_heuristic(line)
            claims.append(
                TechnicalClaim(
                    statement=line,
                    category=category,
                    technologies=techs,
                    verifiable=len(techs) > 0 or len(line.split()) >= 6,
                    source_context=line,
                )
            )

    if not claims and len(text) >= 20:
        techs = detect_technologies_in_text(text)
        sample = text[:150].strip()
        preview = ", ".join(techs[:4]) or "modular components"
        claims.append(
            TechnicalClaim(
                statement=f"Architected system utilizing {preview}.",
                category=ClaimCategory.ARCHITECTURE,
                technologies=techs,
                verifiable=True,
                source_context=sample,
            )
        )

    return claims


async def _call_llm_for_claims(user_prompt: str) -> str | None:
    """Calls LiteLLM asynchronously to extract structured technical claims."""
    if not settings.FREELLMAPI_API_KEY:
        logger.info("llm_api_key_not_configured_skipping_llm")
        return None

    messages = [
        {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    kwargs = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
        "api_key": settings.FREELLMAPI_API_KEY,
    }
    if settings.FREELLMAPI_BASE_URL:
        kwargs["api_base"] = settings.FREELLMAPI_BASE_URL

    try:
        response = await litellm.acompletion(**kwargs)
        raw_content = response.choices[0].message.content or ""
        return clean_json_response(raw_content)
    except Exception as exc:
        logger.warning("claim_extraction_llm_failed", error=str(exc))
        return None


async def extract_technical_claims(text: str) -> ClaimExtractionResponse:
    """Extracts, categorizes, and grounds technical claims from resume or profile text."""
    clean_text = text[:50000].strip()
    if len(clean_text) < 10:
        raise ValueError(
            "Resume text is too short for meaningful claim extraction (min 10 chars)."
        )

    source_char_count = len(clean_text)
    user_prompt = format_claim_extraction_user_prompt(clean_text)
    cleaned = await _call_llm_for_claims(user_prompt)

    claims: list[TechnicalClaim] = []

    if cleaned:
        try:
            data: Any = json.loads(cleaned)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "statement" in item:
                        category_str = str(item.get("category", "architecture")).lower()
                        valid_categories = {c.value for c in ClaimCategory}
                        cat = (
                            ClaimCategory(category_str)
                            if category_str in valid_categories
                            else _classify_category_heuristic(item["statement"])
                        )
                        raw_techs = item.get("technologies", [])
                        tech_list = (
                            [str(t) for t in raw_techs] if isinstance(raw_techs, list) else []
                        )
                        if not tech_list:
                            tech_list = detect_technologies_in_text(item["statement"])

                        claims.append(
                            TechnicalClaim(
                                statement=str(item["statement"]).strip(),
                                category=cat,
                                technologies=tech_list,
                                verifiable=bool(item.get("verifiable", True)),
                                source_context=str(
                                    item.get("source_context", item["statement"])
                                ).strip(),
                            )
                        )
        except Exception as parse_exc:
            logger.warning("claim_extraction_json_parse_failed", error=str(parse_exc))
            claims = []

    if not claims:
        claims = _deterministic_fallback_claims(clean_text)

    all_techs = set()
    for c in claims:
        all_techs.update(c.technologies)
    all_techs.update(detect_technologies_in_text(clean_text))

    return ClaimExtractionResponse(
        claims=claims,
        total_claims=len(claims),
        source_char_count=source_char_count,
        technologies_detected=sorted(all_techs),
    )
