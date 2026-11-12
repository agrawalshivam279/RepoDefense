"""Pydantic schemas and data contracts for Architecture Defense Mode."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import validate_llm_base_url
from app.schemas.architecture import DetectedPattern
from app.schemas.diagram import DiagramEdge, DiagramNode, DiagramType


class ArchFocusAreaType(str, Enum):
    """High-level architectural axes interrogated during defense."""

    PATTERN_CHOICE = "PATTERN_CHOICE"
    COMPONENT_BOUNDARY = "COMPONENT_BOUNDARY"
    DATA_FLOW_COUPLING = "DATA_FLOW_COUPLING"
    ARCHITECTURAL_RISK = "ARCHITECTURAL_RISK"


class ArchDefenseStage(str, Enum):
    """Discrete FSM states of the architecture defense loop."""

    TOPIC_ACTIVE = "TOPIC_ACTIVE"
    TRADEOFF_CHALLENGE = "TRADEOFF_CHALLENGE"
    COMPLETED = "COMPLETED"


class DiagramTarget(BaseModel):
    """Diagram node and connected edges anchored to an architectural topic."""

    node_id: str = Field(..., description="DiagramNode identifier from repository diagram")
    label: str = Field(..., description="Human-readable component label")
    node_type: str = Field(default="service", description="Component category in diagram")
    subgraph: Optional[str] = Field(default=None, description="Owning architectural layer")
    connected_edges: List[str] = Field(
        default_factory=list,
        description="Formatted directed edge descriptions touching this node",
    )

    model_config = ConfigDict(extra="ignore")


class ArchDefenseTopic(BaseModel):
    """Diagram- and pattern-grounded high-level architecture interrogation topic."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique topic identifier",
    )
    title: str = Field(..., description="Short descriptive title of the design decision")
    focus_area: ArchFocusAreaType = Field(..., description="Architectural axis under review")
    pattern_name: str = Field(..., description="Detected or baseline architectural pattern name")
    severity_or_confidence: str = Field(
        default="HIGH", description="Confidence tier or risk severity rating"
    )
    target_nodes: List[DiagramTarget] = Field(
        default_factory=list, description="Diagram nodes directly interrogated by this topic"
    )
    design_claim: str = Field(..., description="Implicit architectural claim inferred from repo")
    interrogation_prompt: str = Field(
        ..., description="Principal Architect question probing high-level design choices"
    )
    expected_tradeoffs: List[str] = Field(
        default_factory=list, description="Architectural tradeoffs candidate should defend"
    )
    risk_references: List[str] = Field(
        default_factory=list, description="Linked architectural risk titles or evidence keys"
    )

    model_config = ConfigDict(extra="ignore")


class ArchDefenseTurn(BaseModel):
    """Single dialogue exchange within an architecture defense session."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique turn identifier",
    )
    role: str = Field(..., description="Speaker role: interviewer, candidate, or system")
    content: str = Field(..., description="Dialogue turn content")
    stage: ArchDefenseStage = Field(..., description="FSM stage when turn was recorded")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Structured rubric scores and evaluation signals"
    )

    model_config = ConfigDict(extra="ignore")


class ArchDefenseEvaluationOutput(BaseModel):
    """Structured rubric evaluation returned by the Principal Architect evaluator."""

    depth_score: int = Field(..., ge=1, le=10, description="Architectural depth score (1-10)")
    pattern_rationale_solid: bool = Field(
        ..., description="True if candidate justified why this topology fits constraints"
    )
    tradeoffs_articulated: bool = Field(
        ..., description="True if candidate weighed coupling, cost, consistency, or complexity"
    )
    boundary_coherence_score: int = Field(
        ..., ge=1, le=10, description="Clarity of layer/module boundary justification (1-10)"
    )
    feedback: str = Field(..., description="Principal Architect critique and rationale review")
    follow_up_challenge: Optional[str] = Field(
        default=None,
        description="Follow-up tradeoff or alternative architecture probe when advancing",
    )
    is_terminal: bool = Field(
        default=False, description="True if session should terminate after this turn"
    )

    model_config = ConfigDict(extra="ignore")


class ArchDefenseSessionState(BaseModel):
    """Active or completed state of an architecture defense interview session."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    project_id: str = Field(..., description="Owning project ID")
    topic: ArchDefenseTopic = Field(..., description="Selected architectural topic under defense")
    mermaid_code: str = Field(..., description="Mermaid architecture diagram for side-by-side view")
    diagram_summary: str = Field(..., description="Summary of the repository topology diagram")
    primary_pattern_name: str = Field(..., description="Primary detected pattern name")
    stage: ArchDefenseStage = Field(
        default=ArchDefenseStage.TOPIC_ACTIVE,
        description="Current FSM state of the defense session",
    )
    current_turn_index: int = Field(default=0, description="Pointer to current dialogue turn")
    turns: List[ArchDefenseTurn] = Field(
        default_factory=list, description="Ordered conversational transcript"
    )
    overall_score: Optional[float] = Field(
        default=None, description="Final aggregate score between 1.0 and 10.0"
    )
    pattern_rationale_solid: Optional[bool] = Field(
        default=None, description="Whether pattern choice rationale held up under interrogation"
    )
    boundary_coherence_score: Optional[int] = Field(
        default=None, description="Boundary coherence score (1-10)"
    )
    feedback: Optional[str] = Field(default=None, description="Closing architectural assessment")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Session creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Last updated UTC timestamp",
    )

    model_config = ConfigDict(extra="ignore")


class _LLMOverrideBase(BaseModel):
    """Shared optional LLM override fields with strict HTTPS allowlist validation."""

    model: Optional[str] = Field(
        default=None, max_length=120, description="Optional LLM model override"
    )
    api_key: Optional[str] = Field(
        default=None, max_length=256, description="Optional LLM API key override"
    )
    base_url: Optional[str] = Field(
        default=None, max_length=256, description="Optional LLM base URL override"
    )

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: Optional[str]) -> Optional[str]:
        return validate_llm_base_url(value)


class GenerateArchTopicsRequest(_LLMOverrideBase):
    """Request payload to synthesize or retrieve diagram-grounded architecture defense topics."""

    focus_area: Optional[ArchFocusAreaType] = Field(
        default=None, description="Optional filter by architectural focus area"
    )
    max_topics: int = Field(
        default=4, ge=1, le=10, description="Maximum number of defense topics to return"
    )


class ArchTopicListResponse(BaseModel):
    """Response bundling synthesized defense topics with repository diagram & pattern context."""

    project_id: str
    project_name: str
    primary_pattern: DetectedPattern
    diagram_type: DiagramType
    mermaid_code: str
    nodes: List[DiagramNode] = Field(default_factory=list)
    edges: List[DiagramEdge] = Field(default_factory=list)
    is_diagram_fallback: bool
    total_topics: int
    topics: List[ArchDefenseTopic]


class StartArchDefenseRequest(_LLMOverrideBase):
    """Request payload to start an architecture defense session on a selected topic."""

    topic_id: str = Field(..., min_length=1, max_length=64, description="Target topic ID")


class SubmitArchAnswerRequest(_LLMOverrideBase):
    """Request payload submitting a candidate's architectural defense explanation."""

    answer: str = Field(
        ..., min_length=1, max_length=8000, description="Candidate architectural defense"
    )
