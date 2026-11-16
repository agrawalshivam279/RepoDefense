"""Pydantic v2 schemas for candidate skills, proficiencies, and weaknesses."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WeaknessSeverity(str, Enum):
    """Severity tier for an identified architectural or technical gap."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class SkillCategory(str, Enum):
    """Canonical technical competency categories."""

    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    CONCURRENCY = "concurrency"
    TRADEOFFS = "tradeoffs"
    CODE_QUALITY = "code_quality"
    DEVOPS_SRE = "devops_sre"


class UserSkillBase(BaseModel):
    """Base schema for a tracked candidate technical skill."""

    category: str = Field(
        ..., max_length=64, description="High-level category, e.g. architecture"
    )
    topic: str = Field(
        ..., max_length=128, description="Specific skill or topic, e.g. connection_pooling"
    )
    proficiency_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Proficiency percentage between 0.0 and 100.0",
    )
    total_evaluations: int = Field(default=0, ge=0, description="Total assessments")
    passed_evaluations: int = Field(default=0, ge=0, description="Passed assessments")
    failed_evaluations: int = Field(default=0, ge=0, description="Failed assessments")


class UserSkillCreate(UserSkillBase):
    """Schema for initializing a candidate user skill record."""

    user_id: uuid.UUID = Field(..., description="Associated candidate user ID")


class UserSkillUpdate(BaseModel):
    """Schema for updating a skill proficiency score after a defense turn."""

    proficiency_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="New proficiency score"
    )
    passed: Optional[bool] = Field(
        default=None, description="Whether the recent evaluation was passed"
    )
    last_evaluated_at: Optional[datetime] = Field(
        default=None, description="Timestamp of the evaluation"
    )

    model_config = ConfigDict(extra="ignore")


class UserSkillResponse(UserSkillBase):
    """Public serialized representation of a user skill."""

    id: uuid.UUID
    user_id: uuid.UUID
    last_evaluated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateWeaknessBase(BaseModel):
    """Base attributes for an identified weakness or blind spot."""

    simulation_mode: str = Field(
        ...,
        max_length=32,
        description="Originating simulation mode key (e.g. core_defense, stress_test)",
    )
    category: str = Field(
        ..., max_length=64, description="Technical category, e.g. scalability"
    )
    topic: str = Field(
        ..., max_length=128, description="Specific topic where the gap was observed"
    )
    severity: WeaknessSeverity = Field(
        default=WeaknessSeverity.MAJOR, description="Severity tier"
    )
    question_prompt: str = Field(
        ..., description="The challenge or question that exposed the gap"
    )
    candidate_response: Optional[str] = Field(
        default=None, description="Candidate response text if available"
    )
    feedback: str = Field(
        ..., description="Evaluator feedback explaining the architectural risk"
    )


class CandidateWeaknessCreate(CandidateWeaknessBase):
    """Schema for recording a new weakness from a simulation evaluation."""

    user_id: uuid.UUID = Field(..., description="Associated candidate user ID")
    project_id: uuid.UUID = Field(..., description="Associated repository project ID")
    session_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional simulation session ID reference",
    )
    topic_embedding: Optional[List[float]] = Field(
        default=None, description="Optional 384-dimensional vector embedding"
    )

    @field_validator("topic_embedding")
    @classmethod
    def validate_embedding_dimensions(
        cls, v: Optional[List[float]]
    ) -> Optional[List[float]]:
        if v is not None and len(v) != 384:
            raise ValueError(
                f"topic_embedding must contain exactly 384 dimensions, got {len(v)}"
            )
        return v


class CandidateWeaknessUpdate(BaseModel):
    """Schema for marking a weakness as resolved or appending mentor feedback."""

    resolved: Optional[bool] = Field(
        default=None, description="Resolution status (True when re-test is passed)"
    )
    resolved_at: Optional[datetime] = Field(
        default=None, description="Timestamp of resolution"
    )
    feedback: Optional[str] = Field(
        default=None, description="Updated or appended mentor advice"
    )

    model_config = ConfigDict(extra="ignore")


class CandidateWeaknessResponse(CandidateWeaknessBase):
    """Public serialized representation of an identified weakness."""

    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    session_id: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    has_embedding: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def derive_has_embedding(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "has_embedding" not in data and "topic_embedding" in data:
                data["has_embedding"] = data["topic_embedding"] is not None
        return data


class UserSkillsOverviewResponse(BaseModel):
    """Aggregated portfolio summary of candidate strengths, weaknesses, and metrics."""

    user_id: uuid.UUID
    total_skills_tracked: int = Field(default=0, ge=0)
    avg_proficiency_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    weak_skills_count: int = Field(default=0, ge=0)
    strong_skills_count: int = Field(default=0, ge=0)
    unresolved_weaknesses_count: int = Field(default=0, ge=0)
    resolved_weaknesses_count: int = Field(default=0, ge=0)
    top_weaknesses: List[CandidateWeaknessResponse] = Field(default_factory=list)
    skills: List[UserSkillResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)



class RecordEvaluationRequest(BaseModel):
    """Payload for submitting a simulation evaluation turn result."""

    project_id: uuid.UUID = Field(..., description="Target repository project ID")
    simulation_mode: str = Field(..., max_length=32, description="Simulation mode key")
    category: str = Field(..., max_length=64, description="Technical skill category")
    topic: str = Field(..., max_length=128, description="Specific topic or skill")
    question_prompt: str = Field(..., description="Challenge prompt or question")
    feedback: str = Field(..., description="Evaluation feedback or explanation")
    passed: bool = Field(..., description="Whether the candidate passed the turn")
    score: float = Field(default=50.0, ge=0.0, le=100.0, description="Evaluation score")
    session_id: Optional[str] = Field(
        default=None, max_length=64, description="Session reference"
    )
    candidate_response: Optional[str] = Field(
        default=None, description="Candidate answer text"
    )
    severity: Optional[WeaknessSeverity] = Field(
        default=None, description="Optional gap severity"
    )


class RecordEvaluationResponse(BaseModel):
    """Result of processing a simulation evaluation turn."""

    skill: UserSkillResponse
    weakness: Optional[CandidateWeaknessResponse] = None

    model_config = ConfigDict(from_attributes=True)
