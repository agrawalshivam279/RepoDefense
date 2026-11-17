"""Pydantic v2 schemas and data contracts for Targeted Re-Testing."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TargetedRetestSessionCreate(BaseModel):
    """Payload to initiate a targeted re-test session."""

    model_config = ConfigDict(extra="forbid")

    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional project scope to filter candidate weaknesses",
    )
    weakness_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="Optional explicit list of active weakness IDs to re-test",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional category filter (e.g. concurrency, caching, security)",
    )
    max_questions: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of targeted re-test questions to generate",
    )

    @field_validator("category")
    @classmethod
    def sanitize_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            return v if v else None
        return None


class RetestQuestion(BaseModel):
    """A targeted re-test question crafted to verify weakness remediation."""

    model_config = ConfigDict(from_attributes=True)

    question_id: str = Field(
        ...,
        description="Unique identifier for this re-test question turn",
    )
    weakness_id: uuid.UUID = Field(
        ...,
        description="The specific CandidateWeakness ID being tested",
    )
    category: str = Field(
        ...,
        max_length=64,
        description="Technical domain category",
    )
    topic: str = Field(
        ...,
        max_length=128,
        description="Architectural mechanism being tested",
    )
    severity: str = Field(
        ...,
        description="Severity level of the original weakness (critical, major, minor)",
    )
    original_prompt: str = Field(
        ...,
        description="The original question prompt that uncovered the weakness",
    )
    question_text: str = Field(
        ...,
        description="The targeted re-test question asking the candidate to defend remediation",
    )
    architectural_constraint: str = Field(
        ...,
        description="The specific production constraint or edge case to address",
    )
    evaluation_rubric: str = Field(
        ...,
        description="Criteria required to pass the re-test",
    )


class TargetedRetestSessionResponse(BaseModel):
    """Structured response containing generated targeted re-test session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(
        ...,
        description="Unique identifier for the active re-test session",
    )
    user_id: uuid.UUID = Field(
        ...,
        description="Authenticated candidate user ID",
    )
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Associated project ID if scoped to a project",
    )
    total_questions: int = Field(
        ...,
        description="Total number of re-test questions in this session",
    )
    questions: List[RetestQuestion] = Field(
        default_factory=list,
        description="List of targeted re-test questions",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation timestamp",
    )


class SubmitRetestAnswerRequest(BaseModel):
    """Candidate's submission defending their remediation of a targeted weakness."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identifier of the active re-test session",
    )
    question_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identifier of the re-test question",
    )
    weakness_id: uuid.UUID = Field(
        ...,
        description="CandidateWeakness ID targeted by this question",
    )
    candidate_response: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The candidate's detailed architectural defense",
    )

    @field_validator("candidate_response")
    @classmethod
    def clean_response(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 10:
            raise ValueError("Candidate defense must be at least 10 characters long")
        return clean


class RetestEvaluationResponse(BaseModel):
    """Structured evaluation outcome of a candidate's re-test submission."""

    model_config = ConfigDict(from_attributes=True)

    question_id: str = Field(
        ...,
        description="Question identifier",
    )
    weakness_id: uuid.UUID = Field(
        ...,
        description="Evaluated weakness identifier",
    )
    passed: bool = Field(
        ...,
        description="Whether the candidate's answer demonstrated sufficient remediation",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Quantitative score from 0.0 to 100.0",
    )
    feedback: str = Field(
        ...,
        description="Detailed mentor feedback on the response",
    )
    key_improvements: List[str] = Field(
        default_factory=list,
        description="Positive aspects or correct architectural remedies identified",
    )
    remaining_gaps: List[str] = Field(
        default_factory=list,
        description="Unresolved gaps or nuances requiring further study",
    )
    weakness_resolved: bool = Field(
        ...,
        description="Whether the CandidateWeakness was marked resolved in the database",
    )
    updated_proficiency: Optional[float] = Field(
        default=None,
        description="Updated skill proficiency score if reinforced",
    )


class EligibleWeaknessItem(BaseModel):
    """A candidate weakness available for targeted re-testing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Weakness ID")
    project_id: Optional[uuid.UUID] = Field(default=None, description="Project ID")
    category: str = Field(..., description="Category")
    topic: str = Field(..., description="Topic")
    severity: str = Field(..., description="Severity tier")
    original_prompt: str = Field(..., description="Original prompt")
    feedback: str = Field(..., description="Original mentor feedback")
    created_at: datetime = Field(..., description="Date detected")


class EligibleWeaknessesResponse(BaseModel):
    """Collection of unresolved weaknesses eligible for re-test."""

    model_config = ConfigDict(from_attributes=True)

    total_eligible: int = Field(..., description="Total unresolved weaknesses")
    weaknesses: List[EligibleWeaknessItem] = Field(
        default_factory=list,
        description="List of candidate weaknesses available for re-testing",
    )
