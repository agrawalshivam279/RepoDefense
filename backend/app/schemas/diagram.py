"""Pydantic v2 data models for architecture diagrams and Mermaid flowchart syntax."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DiagramType(str, Enum):
    """Supported Mermaid diagram types."""

    FLOWCHART_TD = "flowchart TD"
    FLOWCHART_LR = "flowchart LR"


class DiagramNode(BaseModel):
    """Node in an architectural diagram."""

    node_id: str = Field(..., description="Alphanumeric identifier for Mermaid node")
    label: str = Field(..., description="Human-readable display label")
    node_type: str = Field(
        ...,
        description="'frontend' | 'backend' | 'database' | 'queue' | 'external' | 'service'",
    )
    subgraph: str | None = Field(default=None, description="Optional enclosing subgraph/tier name")

    model_config = ConfigDict(from_attributes=True)


class DiagramEdge(BaseModel):
    """Directional relationship between two architecture nodes."""

    source_id: str
    target_id: str
    label: str | None = None
    style: str | None = "solid"

    model_config = ConfigDict(from_attributes=True)


class DiagramResponse(BaseModel):
    """Complete architecture diagram response with raw Mermaid code and structured graph."""

    project_id: str
    project_name: str
    diagram_type: DiagramType = DiagramType.FLOWCHART_TD
    mermaid_code: str = Field(..., description="Valid raw Mermaid flowchart definition")
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    is_fallback: bool = Field(default=False)
    summary: str

    model_config = ConfigDict(from_attributes=True)
