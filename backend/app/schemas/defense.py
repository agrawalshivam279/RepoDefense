"""Pydantic schemas and data contracts for defense interview sessions and state machine."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import GroundedQuestion


class DefenseStage(str, Enum):
    """Discrete states of the defense interview state machine."""

    INITIALIZING = "initializing"
    QUESTION_ACTIVE = "question_active"
    EVALUATING_DEFENSE = "evaluating_defense"
    STRESS_TEST_ACTIVE = "stress_test_active"
    MENTOR_ACTIVE = "mentor_active"
    QUESTION_COMPLETED = "question_completed"
    SESSION_COMPLETED = "session_completed"


class TurnRole(str, Enum):
    """Participants in the defense interview turn exchange."""

    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


class DefenseTurn(BaseModel):
    """Single turn / utterance in the defense dialogue transcript."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique turn identifier",
    )
    role: TurnRole = Field(..., description="Role of the speaker")
    content: str = Field(..., description="Text content of the turn")
    stage: DefenseStage = Field(..., description="Interview state during this turn")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary turn metadata (scores, hints, cited files)",
    )

    model_config = ConfigDict(extra="ignore")


class DefenseQuestionProgress(BaseModel):
    """Lifecycle tracking for an individual question during a defense session."""

    question: GroundedQuestion
    status: DefenseStage = DefenseStage.QUESTION_ACTIVE
    initial_defense: Optional[str] = None
    defense_score: Optional[int] = None
    stress_test_prompt: Optional[str] = None
    stress_test_response: Optional[str] = None
    mentor_hint: Optional[str] = None
    retest_question: Optional[str] = None
    retest_response: Optional[str] = None
    final_score: Optional[int] = None
    feedback: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class DefenseSessionState(BaseModel):
    """Canonical representation of an active or completed defense session."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    project_id: str = Field(..., description="Target project ID")
    status: DefenseStage = Field(
        default=DefenseStage.QUESTION_ACTIVE,
        description="Current state of the interview FSM",
    )
    current_question_index: int = Field(
        default=0,
        description="0-indexed pointer to active question",
    )
    total_questions: int = Field(
        default=0,
        description="Total number of questions in this defense session",
    )
    questions: List[DefenseQuestionProgress] = Field(
        default_factory=list,
        description="Ordered list of questions and individual progress",
    )
    turns: List[DefenseTurn] = Field(
        default_factory=list,
        description="Full chronological transcript of the defense dialogue",
    )
    overall_score: Optional[float] = Field(
        None,
        description="Aggregate defense score across all questions (1.0 to 10.0)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Session creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Last updated timestamp",
    )

    model_config = ConfigDict(extra="ignore")


class StartDefenseRequest(BaseModel):
    """Payload to initiate a defense session for a repository."""

    num_questions: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of evidence-grounded questions to include (1-5)",
    )
    custom_categories: Optional[List[str]] = Field(
        None,
        description="Optional subset of categories to prioritize",
    )


class SubmitAnswerRequest(BaseModel):
    """Payload submitted by a candidate defending their code or answering a stress test."""

    answer: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Candidate's architectural defense or response",
    )


class EvaluationOutput(BaseModel):
    """Structured output returned by the LLM evaluator for an initial defense."""

    passed_initial_defense: bool = Field(
        ...,
        description="True if defense is technically sound and grounded in repository facts",
    )
    depth_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Technical depth rating from 1 to 10",
    )
    grounding_verified: bool = Field(
        ...,
        description="True if answer correctly reflects the actual codebase architecture",
    )
    feedback: str = Field(
        ...,
        description="Principal Engineer assessment of the candidate's explanation",
    )
    stress_test_prompt: Optional[str] = Field(
        None,
        description="Follow-up production bottleneck constraint if candidate passed",
    )
    mentor_hint: Optional[str] = Field(
        None,
        description="Constructive guidance and architectural hints if candidate struggled",
    )
    retest_question: Optional[str] = Field(
        None,
        description="Guided follow-up variant question if candidate struggled",
    )

    model_config = ConfigDict(extra="ignore")


class SecondaryEvaluationOutput(BaseModel):
    """Structured output for evaluating follow-up stress test or re-test answers."""

    handled_successfully: bool = Field(
        ...,
        description="True if candidate adequately answered the follow-up scenario",
    )
    follow_up_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Rating from 1 to 10 for the follow-up answer",
    )
    feedback: str = Field(
        ...,
        description="Constructive evaluation of the candidate's follow-up response",
    )

    model_config = ConfigDict(extra="ignore")
