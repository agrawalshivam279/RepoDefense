"""Pydantic v2 schemas and data contracts for Mentor Mode teaching content."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.skill import SkillCategory


class CodeRemediationSnippet(BaseModel):
    """Concrete Before-and-After code remediation for an architectural anti-pattern."""

    title: str = Field(
        ...,
        max_length=128,
        description="Concise description of the remediation pattern",
    )
    language: str = Field(
        default="python",
        max_length=32,
        description="Programming language identifier (e.g. python, typescript)",
    )
    file_context: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Illustrative relative file path context, e.g. app/core/database.py",
    )
    before_code: str = Field(
        ...,
        description="The flawed, vulnerable, or suboptimal implementation",
    )
    after_code: str = Field(
        ...,
        description="The hardened, production-grade architectural remediation",
    )
    explanation: str = Field(
        ...,
        description="Architectural rationale explaining why this transformation resolves the risk",
    )


class MentorExplanationRequest(BaseModel):
    """Request payload to synthesize a mentor explanation and code remediation."""

    weakness_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional ID of a tracked CandidateWeakness to load context from",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Technical category (e.g. architecture, scalability, concurrency)",
    )
    topic: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Specific technical topic or mechanism (e.g. connection_pooling)",
    )
    question_prompt: Optional[str] = Field(
        default=None,
        description="The original challenge or question that exposed the candidate gap",
    )
    candidate_response: Optional[str] = Field(
        default=None,
        description="The candidate's response or reasoning that required mentoring",
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Evaluator notes or summary of the gap",
    )
    code_context: Optional[str] = Field(
        default=None,
        description="Optional code excerpt or evidence relevant to the question",
    )
    language: str = Field(
        default="python",
        max_length=32,
        description="Target programming language for synthesized code examples",
    )
    # LLM Overrides (for testing & flexible routing)
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

    @model_validator(mode="after")
    def validate_request_source(self) -> "MentorExplanationRequest":
        """Ensure either weakness_id is set or minimum topic context is provided."""
        if not self.weakness_id and not (self.topic and self.topic.strip()):
            raise ValueError(
                "Either 'weakness_id' or a non-empty 'topic' must be provided."
            )
        if not self.weakness_id and not self.category:
            self.category = SkillCategory.ARCHITECTURE.value
        return self


class MentorExplanationResponse(BaseModel):
    """Structured architectural teaching content and drop-in code remediation."""

    explanation_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for this generated explanation session",
    )
    category: str = Field(
        ...,
        description="Canonical technical category of the concept",
    )
    topic: str = Field(
        ...,
        description="Specific topic or mechanism being mentored",
    )
    architectural_risk: str = Field(
        ...,
        description="Detailed breakdown of the failure mode, bottleneck, or vulnerability",
    )
    core_concept: str = Field(
        ...,
        description="Underlying software engineering design principle or architectural pattern",
    )
    mentor_advice: str = Field(
        ...,
        description="Constructive, pedagogical guidance from the Principal Engineer persona",
    )
    code_examples: List[CodeRemediationSnippet] = Field(
        default_factory=list,
        description="Concrete Before-and-After code remediation examples",
    )
    key_takeaways: List[str] = Field(
        default_factory=list,
        description="Key engineering principles to remember (2-4 bullet points)",
    )
    socratic_followup: str = Field(
        ...,
        description="Socratic challenge question preparing the candidate for a re-test",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC generation timestamp",
    )

    model_config = ConfigDict(from_attributes=True)
