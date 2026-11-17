"""Pydantic v2 schemas and data contracts for Mentor Mode Mini Challenges."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import validate_llm_base_url
from app.schemas.skill import SkillCategory


class MiniChallengeDifficulty(str, Enum):
    """Difficulty tier for an architectural mini-challenge."""

    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MiniChallengeResponse(BaseModel):
    """Structured architectural mini-challenge presented to the candidate."""

    challenge_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the challenge instance",
    )
    category: str = Field(
        ...,
        max_length=64,
        description="Canonical technical category (e.g. scalability, concurrency, caching)",
    )
    topic: str = Field(
        ...,
        max_length=128,
        description="Specific architectural mechanism being tested (e.g. connection_pooling)",
    )
    difficulty: MiniChallengeDifficulty = Field(
        default=MiniChallengeDifficulty.INTERMEDIATE,
        description="Difficulty level of the challenge",
    )
    title: str = Field(
        ...,
        max_length=160,
        description="Concise, descriptive title for the challenge",
    )
    scenario: str = Field(
        ...,
        description="Architectural context and problem statement describing the production issue",
    )
    starter_code: Optional[str] = Field(
        default=None,
        description="Optional flawed or skeleton code snippet that needs refactoring",
    )
    language: str = Field(
        default="python",
        max_length=32,
        description="Target programming language (e.g. python, typescript)",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="Specific architectural acceptance criteria the solution must satisfy",
    )
    hints: List[str] = Field(
        default_factory=list,
        description="Progressive Socratic hints to guide the candidate",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC generation timestamp",
    )

    model_config = ConfigDict(from_attributes=True)


class GenerateChallengeRequest(BaseModel):
    """Request payload to generate a targeted architectural mini-challenge."""

    weakness_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional ID of a tracked CandidateWeakness to ground the challenge in",
    )
    topic: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Specific topic or anti-pattern to test",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Technical category (e.g. scalability, architecture)",
    )
    difficulty: MiniChallengeDifficulty = Field(
        default=MiniChallengeDifficulty.INTERMEDIATE,
        description="Requested challenge difficulty level",
    )
    language: str = Field(
        default="python",
        max_length=32,
        description="Programming language for the starter snippet",
    )
    code_context: Optional[str] = Field(
        default=None,
        description="Optional repository code snippet to anchor the challenge in real code",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM model override",
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM base URL override",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM API key override",
    )

    @field_validator("llm_base_url")
    @classmethod
    def _validate_base_url(cls, value: Optional[str]) -> Optional[str]:
        return validate_llm_base_url(value)

    @model_validator(mode="after")
    def validate_request_source(self) -> "GenerateChallengeRequest":
        """Ensure either weakness_id is set or minimum topic context is provided."""
        if not self.weakness_id and not (self.topic and self.topic.strip()):
            raise ValueError(
                "Either 'weakness_id' or a non-empty 'topic' must be provided."
            )
        if not self.weakness_id and not self.category:
            self.category = SkillCategory.ARCHITECTURE.value
        return self


class SubmitChallengeSolutionRequest(BaseModel):
    """Candidate's submitted solution for an architectural mini-challenge."""

    challenge_id: uuid.UUID = Field(
        ...,
        description="Identifier of the challenge being solved",
    )
    weakness_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional tracked CandidateWeakness ID to update if passed",
    )
    category: str = Field(
        ...,
        max_length=64,
        description="Category of the challenge",
    )
    topic: str = Field(
        ...,
        max_length=128,
        description="Topic of the challenge",
    )
    scenario: str = Field(
        ...,
        description="The problem statement or scenario text",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="The list of acceptance criteria that were evaluated",
    )
    candidate_solution: str = Field(
        ...,
        min_length=10,
        description="Candidate's proposed refactored code or architectural explanation",
    )
    language: str = Field(
        default="python",
        max_length=32,
        description="Language used in the solution",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM model override",
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM base URL override",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="Optional LiteLLM API key override",
    )

    @field_validator("llm_base_url")
    @classmethod
    def _validate_base_url(cls, value: Optional[str]) -> Optional[str]:
        return validate_llm_base_url(value)


class ChallengeEvaluationResponse(BaseModel):
    """Principal Engineer evaluation of the candidate's challenge solution."""

    evaluation_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the evaluation result",
    )
    challenge_id: uuid.UUID = Field(
        ...,
        description="Identifier of the evaluated challenge",
    )
    passed: bool = Field(
        ...,
        description="Whether the solution satisfies production architectural standards",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Evaluation score from 0.0 to 100.0",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Architectural merits and strengths identified in the solution",
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="Requirements or safety mechanisms omitted from the solution",
    )
    critique: str = Field(
        ...,
        description="Principal Engineer constructive critique explaining the grading",
    )
    model_solution: str = Field(
        ...,
        description="Canonical production reference solution demonstrating best practice",
    )
    weakness_updated: bool = Field(
        default=False,
        description="Whether a linked CandidateWeakness and UserSkill was updated",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC evaluation timestamp",
    )

    model_config = ConfigDict(from_attributes=True)
