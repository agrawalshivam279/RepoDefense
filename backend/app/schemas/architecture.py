from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ArchitecturePatternType(str, Enum):
    """Supported high-level repository architectural pattern categories."""

    MODULAR_MONOLITH = "modular_monolith"
    MVC = "mvc"
    CLEAN_ARCHITECTURE = "clean_architecture"
    LAYERED_ARCHITECTURE = "layered_architecture"
    EVENT_DRIVEN = "event_driven"
    MICROSERVICES = "microservices"
    SERVERLESS_JAMSTACK = "serverless_jamstack"
    UNSTRUCTURED = "unstructured"


class PatternConfidenceTier(str, Enum):
    """Confidence categorization based on deterministic heuristic weights."""

    HIGH = "high"  # >= 0.75
    MODERATE = "moderate"  # 0.45 - 0.74
    LOW = "low"  # < 0.45


class PatternIndicator(BaseModel):
    """Concrete evidence signal supporting an architectural pattern."""

    indicator_type: str = Field(..., description="'directory', 'dependency', or 'evidence'")
    description: str = Field(..., description="Human-readable explanation of the signal")
    weight: float = Field(..., ge=0.0, le=1.0, description="Heuristic contribution weight")
    matched_items: list[str] = Field(
        default_factory=list, description="Specific matched paths, packages, or evidence"
    )

    model_config = ConfigDict(from_attributes=True)


class DetectedPattern(BaseModel):
    """Evaluated architectural pattern with confidence score and indicators."""

    pattern_type: ArchitecturePatternType
    pattern_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    tier: PatternConfidenceTier
    summary: str
    indicators: list[PatternIndicator] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ArchitecturalRisk(BaseModel):
    """Detected architectural smell, anti-pattern, or design risk."""

    risk_id: str
    severity: str = Field(..., description="'critical', 'high', 'medium', or 'low'")
    title: str
    description: str
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


class ArchitectureReportResponse(BaseModel):
    """Full architecture audit response containing primary pattern and risks."""

    project_id: str
    project_name: str
    primary_pattern: DetectedPattern
    secondary_patterns: list[DetectedPattern] = Field(default_factory=list)
    all_patterns: list[DetectedPattern] = Field(default_factory=list)
    architectural_risks: list[ArchitecturalRisk] = Field(default_factory=list)
    directory_summary: dict[str, int] = Field(default_factory=dict)
    total_files_analyzed: int = Field(default=0)

    model_config = ConfigDict(from_attributes=True)
