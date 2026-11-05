"""Pydantic v2 schemas for technical claim verification against codebase evidence."""

import uuid
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.claim import TechnicalClaim


class VerificationStatus(StrEnum):
    """Grounding status of a candidate's technical claim against codebase truth."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"


class EvidenceCitation(BaseModel):
    """Specific code chunk or architectural evidence cited to verify or dispute a claim."""

    model_config = ConfigDict(extra="ignore")

    file_path: str = Field(..., description="Repository relative file path.")
    start_line: Optional[int] = Field(
        default=None, description="Starting line number in source file."
    )
    end_line: Optional[int] = Field(
        default=None, description="Ending line number in source file."
    )
    symbol_name: Optional[str] = Field(
        default=None, description="AST symbol name (function, class, endpoint) if applicable."
    )
    snippet: str = Field(..., description="Relevant code or configuration excerpt.")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Cosine similarity or heuristic relevance score (0.0 to 1.0).",
    )
    source_type: str = Field(
        default="code_chunk",
        description="Category of citation: 'code_chunk', 'evidence', or 'dependency'.",
    )


class ClaimVerificationResult(BaseModel):
    """Evaluation verdict, confidence, rationale, and citations for a single technical claim."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(..., description="Unique ID of the evaluated technical claim.")
    statement: str = Field(..., description="The technical claim statement being evaluated.")
    status: VerificationStatus = Field(
        ..., description="Verification verdict: supported, contradicted, or unverifiable."
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level of the verdict based on code evidence (0.0 to 1.0).",
    )
    reasoning: str = Field(
        ..., description="Principal Engineer explanation justifying the verdict."
    )
    citations: List[EvidenceCitation] = Field(
        default_factory=list,
        description="List of concrete code chunks or dependencies grounding the verdict.",
    )
    suggested_defense_questions: List[str] = Field(
        default_factory=list,
        description="1-2 targeted follow-up interview questions to stress-test this claim.",
    )


class ClaimVerificationRequest(BaseModel):
    """Payload for verifying candidate claims against an analyzed repository snapshot."""

    claims: List[TechnicalClaim] = Field(
        ...,
        min_length=1,
        max_length=25,
        description="List of technical claims extracted from candidate resume.",
    )
    top_k_chunks: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Maximum semantic code chunks to retrieve per claim.",
    )
    min_similarity_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity required to include code chunk as evidence.",
    )


class BatchClaimVerificationResponse(BaseModel):
    """Consolidated verification response containing all evaluated claims and metrics."""

    project_id: uuid.UUID = Field(
        ..., description="UUID of the repository project evaluated."
    )
    total_claims: int = Field(
        ..., ge=0, description="Total number of claims processed in this batch."
    )
    verified_claims: List[ClaimVerificationResult] = Field(
        default_factory=list, description="Detailed verification results for each claim."
    )
    summary_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of claims categorized by status (e.g. supported, contradicted).",
    )
