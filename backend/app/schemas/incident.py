"""Pydantic v2 schemas for Chaos Engineering and Incident Simulation Engine."""

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(str, Enum):
    """Broad categorization of simulated system failures."""

    DATABASE_OUTAGE = "DATABASE_OUTAGE"
    DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
    CACHE_FAILURE = "CACHE_FAILURE"
    MESSAGE_BROKER_PARTITION = "MESSAGE_BROKER_PARTITION"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    CONCURRENCY_RACE = "CONCURRENCY_RACE"


class IncidentSeverity(str, Enum):
    """Standard SRE incident severity levels."""

    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_MEDIUM = "P2_MEDIUM"


class IncidentStage(str, Enum):
    """Lifecycle stages for an active incident defense session."""

    TRIAGE = "TRIAGE"
    ESCALATED = "ESCALATED"
    MITIGATED = "MITIGATED"
    POSTMORTEM = "POSTMORTEM"


class ChaosTarget(BaseModel):
    """Architectural code artifact anchoring the simulated failure."""

    file_path: str = Field(..., description="Target file path in repository")
    symbol_name: Optional[str] = Field(default=None, description="Class, function or route name")
    line_start: Optional[int] = Field(default=None, description="Starting line in file")
    line_end: Optional[int] = Field(default=None, description="Ending line in file")
    component_type: str = Field(
        default="service",
        description="Type classification: database, endpoint, worker, cache, client",
    )

    model_config = ConfigDict(extra="ignore")


class IncidentScenario(BaseModel):
    """Hypothetical production outage grounded in code evidence."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this scenario",
    )
    title: str = Field(..., description="Descriptive headline of the outage")
    category: FailureCategory = Field(..., description="Failure archetype")
    severity: IncidentSeverity = Field(..., description="Severity classification")
    hypothetical_trigger: str = Field(
        ..., description="Traffic surge, network partition or external condition"
    )
    symptoms: List[str] = Field(
        default_factory=list, description="Observed production telemetry and error symptoms"
    )
    grounded_target: ChaosTarget = Field(
        ..., description="Specific code anchor that experiences or triggers the fault"
    )
    incident_question: str = Field(
        ..., description="Principal SRE prompt challenging candidate to explain behavior"
    )
    evaluation_criteria: List[str] = Field(
        default_factory=list,
        description="Key resilience concepts expected (e.g. backoff, circuit breaker)",
    )

    model_config = ConfigDict(extra="ignore")


class GenerateScenariosRequest(BaseModel):
    """Request payload to generate chaos scenarios for a project."""

    category: Optional[FailureCategory] = Field(
        default=None, description="Optional category filter"
    )
    limit: int = Field(default=3, ge=1, le=10, description="Max scenarios to return")

    model_config = ConfigDict(extra="ignore")


class ScenarioListResponse(BaseModel):
    """List of generated incident scenarios for a project."""

    project_id: uuid.UUID = Field(..., description="Project ID")
    total_scenarios: int = Field(..., ge=0, description="Total count")
    scenarios: List[IncidentScenario] = Field(default_factory=list, description="Scenarios catalog")

    model_config = ConfigDict(extra="ignore")


class IncidentDefenseTurn(BaseModel):
    """A single dialogue exchange in an incident defense session."""

    turn_index: int = Field(..., ge=1, description="1-indexed turn number")
    prompt: str = Field(..., description="Interviewer challenge or escalation prompt")
    candidate_answer: Optional[str] = Field(default=None, description="Candidate response")
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Turn depth score")
    feedback: Optional[str] = Field(default=None, description="SRE evaluator feedback")
    escalation_injected: Optional[str] = Field(
        default=None, description="Next cascading failure injected"
    )

    model_config = ConfigDict(extra="ignore")


class StartIncidentDefenseRequest(BaseModel):
    """Payload to launch an incident defense session."""

    scenario_id: Optional[str] = Field(
        default=None, description="Pre-generated scenario ID or blank for auto-pick"
    )
    category: Optional[FailureCategory] = Field(
        default=None, description="Category override if scenario_id omitted"
    )

    model_config = ConfigDict(extra="ignore")


class SubmitIncidentAnswerRequest(BaseModel):
    """Candidate answer submission for current incident turn."""

    answer: str = Field(..., min_length=10, max_length=5000, description="Architectural defense")

    model_config = ConfigDict(extra="ignore")


class IncidentDefenseSessionState(BaseModel):
    """Full state machine representation of an active incident defense session."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique incident session ID")
    project_id: uuid.UUID = Field(..., description="Associated Project ID")
    scenario: IncidentScenario = Field(..., description="Active chaos scenario")
    turns: List[IncidentDefenseTurn] = Field(
        default_factory=list, description="Transcript of turns"
    )
    current_turn_index: int = Field(default=1, ge=1, description="Active turn index")
    max_turns: int = Field(default=3, ge=1, le=5, description="Total turns before postmortem")
    stage: IncidentStage = Field(default=IncidentStage.TRIAGE, description="Current incident phase")
    overall_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Aggregate defense score"
    )
    postmortem_summary: Optional[str] = Field(
        default=None, description="Final incident postmortem and architecture summary"
    )

    model_config = ConfigDict(extra="ignore")
