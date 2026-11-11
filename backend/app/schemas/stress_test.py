"""Pydantic schemas and data contracts for stress test and what-if simulation mode."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StressConstraintType(str, Enum):
    """Categories of production scaling constraints."""

    CONCURRENCY_SPIKE = "CONCURRENCY_SPIKE"
    DATA_VOLUME_100X = "DATA_VOLUME_100X"
    MEMORY_PRESSURE = "MEMORY_PRESSURE"
    NETWORK_LATENCY_JITTER = "NETWORK_LATENCY_JITTER"
    DB_CONNECTION_STARVATION = "DB_CONNECTION_STARVATION"


class StressSeverity(str, Enum):
    """Magnitude of the hypothetical scaling constraint."""

    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    EXTREME = "EXTREME"


class StressSessionStage(str, Enum):
    """Discrete states of the stress defense interview loop."""

    SCENARIO_ACTIVE = "SCENARIO_ACTIVE"
    FOLLOW_UP_CONSTRAINED = "FOLLOW_UP_CONSTRAINED"
    COMPLETED = "COMPLETED"


class StressTarget(BaseModel):
    """Codebase component identified as load-bearing."""

    symbol_name: str = Field(..., description="Target function, class, or endpoint name")
    file_path: str = Field(..., description="Repository file path containing the component")
    line_range: str = Field(default="1-10", description="Line span of the target symbol")
    component_type: str = Field(
        default="endpoint", description="Component category (endpoint, model, cache, worker)"
    )

    model_config = ConfigDict(extra="ignore")


class StressTestScenario(BaseModel):
    """A grounded what-if production scaling constraint scenario."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique scenario identifier",
    )
    title: str = Field(..., description="Short descriptive title of the scaling scenario")
    constraint_type: StressConstraintType = Field(..., description="Type of scaling constraint")
    severity: StressSeverity = Field(
        default=StressSeverity.SEVERE, description="Severity magnitude"
    )
    target: StressTarget = Field(..., description="Targeted component")
    context_description: str = Field(..., description="Context of nominal component behavior")
    hypothetical_prompt: str = Field(
        ..., description="Principal Architect what-if prompt interrogating limits"
    )
    expected_tradeoffs: List[str] = Field(
        default_factory=list, description="Architectural tradeoffs candidate should acknowledge"
    )
    cited_evidence_ids: List[str] = Field(
        default_factory=list, description="Linked Evidence or CodeSymbol IDs"
    )

    model_config = ConfigDict(extra="ignore")


class StressDefenseTurn(BaseModel):
    """A single dialogue exchange within the stress defense session."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique turn identifier",
    )
    role: str = Field(..., description="Speaker role: interviewer, candidate, or system")
    content: str = Field(..., description="Text content of the turn")
    stage: StressSessionStage = Field(..., description="Session stage during this turn")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Scoring and feedback metadata"
    )

    model_config = ConfigDict(extra="ignore")


class StressEvaluationOutput(BaseModel):
    """Structured evaluation output returned by the Principal Architect evaluator."""

    depth_score: int = Field(..., ge=1, le=10, description="Technical depth rating from 1 to 10")
    bottleneck_identified: bool = Field(
        ..., description="True if candidate accurately identified the point of failure"
    )
    scaling_strategy_sound: bool = Field(
        ..., description="True if proposed mitigation is architecturally feasible"
    )
    tradeoffs_acknowledged: bool = Field(
        ..., description="True if candidate considered latency, consistency, or cost tradeoffs"
    )
    feedback: str = Field(..., description="Architectural evaluation commentary")
    follow_up_constraint: Optional[str] = Field(
        None, description="Injected secondary constraint if candidate passes stage 1"
    )
    is_terminal: bool = Field(
        default=False, description="True if session should terminate after this turn"
    )

    model_config = ConfigDict(extra="ignore")


class StressDefenseSessionState(BaseModel):
    """Active or completed state of a stress defense session."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    project_id: str = Field(..., description="Target project ID")
    scenario: StressTestScenario = Field(..., description="Scenario under defense")
    stage: StressSessionStage = Field(
        default=StressSessionStage.SCENARIO_ACTIVE,
        description="Current state of the defense session",
    )
    current_turn_index: int = Field(default=0, description="Pointer to current dialogue turn")
    turns: List[StressDefenseTurn] = Field(
        default_factory=list, description="Full conversational transcript"
    )
    overall_score: Optional[float] = Field(
        None, description="Final aggregate score between 1.0 and 10.0"
    )
    bottleneck_identified: Optional[bool] = Field(
        None, description="Whether candidate identified the core bottleneck"
    )
    feedback: Optional[str] = Field(None, description="Summary post-mortem feedback")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Last updated timestamp",
    )

    model_config = ConfigDict(extra="ignore")


class GenerateStressScenariosRequest(BaseModel):
    """Request payload to generate scaling stress test scenarios."""

    constraint_type: Optional[StressConstraintType] = Field(
        None, description="Optional filter by constraint type"
    )
    max_scenarios: int = Field(
        default=4, ge=1, le=10, description="Maximum number of scenarios to synthesize"
    )
    model: Optional[str] = Field(default=None, description="Optional LLM model override")
    api_key: Optional[str] = Field(default=None, description="Optional LLM API key override")
    base_url: Optional[str] = Field(default=None, description="Optional LLM base URL override")


    view_id: Optional[str] = Field(
        default=None, max_length=64, description="Optional active catalog view identifier"
    )
    request_seq: Optional[int] = Field(
        default=None, ge=0, description="Optional monotonic request sequence for view deduplication"
    )


class StressScenarioListResponse(BaseModel):
    """Response containing synthesized scaling scenarios for a repository."""

    project_id: str
    total_scenarios: int
    scenarios: List[StressTestScenario]


class StartStressDefenseRequest(BaseModel):
    """Request payload to initiate a stress defense session."""

    scenario_id: str = Field(..., description="ID of chosen scenario to defend")
    model: Optional[str] = Field(default=None, description="Optional LLM model override")
    api_key: Optional[str] = Field(default=None, description="Optional LLM API key override")
    base_url: Optional[str] = Field(default=None, description="Optional LLM base URL override")


class SubmitStressAnswerRequest(BaseModel):
    """Candidate's submitted response to a scaling challenge or follow-up constraint."""

    answer: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Candidate's architectural scaling explanation",
    )
    model: Optional[str] = Field(default=None, description="Optional LLM model override")
    api_key: Optional[str] = Field(default=None, description="Optional LLM API key override")
    base_url: Optional[str] = Field(default=None, description="Optional LLM base URL override")
