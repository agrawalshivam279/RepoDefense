import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClaimCategory(StrEnum):
    """Domain category for technical claims extracted from developer profiles."""

    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    PERFORMANCE = "performance"
    DATABASE = "database"
    SECURITY = "security"
    FRAMEWORK = "framework"
    INFRASTRUCTURE = "infrastructure"


class TechnicalClaim(BaseModel):
    """A concrete, verifiable technical claim made in a developer resume or profile."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the technical claim.",
    )
    statement: str = Field(
        ...,
        description="Concise statement of the technical decision, architecture, or scaling claim.",
    )
    category: ClaimCategory = Field(
        ...,
        description="Architectural or engineering category of the claim.",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="List of specific technologies, libraries, or tools cited in the claim.",
    )
    verifiable: bool = Field(
        default=True,
        description="Whether this claim contains sufficient technical detail to verify in code.",
    )
    source_context: str = Field(
        default="",
        description="Original sentence or bullet point extracted from the resume.",
    )


class ClaimExtractionRequest(BaseModel):
    """Payload for submitting raw text for technical claim extraction."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Raw resume or project description text content.",
    )


class ClaimExtractionResponse(BaseModel):
    """Structured response containing extracted claims and metadata."""

    claims: list[TechnicalClaim] = Field(
        default_factory=list,
        description="List of extracted and categorized technical claims.",
    )
    total_claims: int = Field(
        ...,
        ge=0,
        description="Total count of technical claims identified.",
    )
    source_char_count: int = Field(
        ...,
        ge=0,
        description="Total character count of the parsed input document.",
    )
    technologies_detected: list[str] = Field(
        default_factory=list,
        description="Deduplicated list of technologies identified across all claims.",
    )
