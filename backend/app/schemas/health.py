from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check payload response model."""

    status: str = Field(default="ok", description="Service health status")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version string")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC server timestamp",
    )


class StoreTelemetry(BaseModel):
    """Telemetry metrics for an in-memory simulation session store."""

    active_sessions: int = Field(..., description="Currently active sessions in memory")
    max_capacity: int = Field(..., description="Maximum allowed sessions before LRU eviction")
    total_created: int = Field(default=0, description="Cumulative sessions created since boot")
    total_evicted: int = Field(default=0, description="Cumulative sessions evicted via LRU")
    total_expired: int = Field(default=0, description="Cumulative sessions pruned via TTL")


class SimulationModeStatus(BaseModel):
    """Operational status and metrics for an individual simulation mode."""

    mode: str = Field(..., description="Mode identifier (e.g., incident_simulation, stress_test)")
    display_name: str = Field(..., description="Human-readable mode title")
    status: str = Field(default="operational", description="operational | degraded | offline")
    active_sessions: int = Field(default=0, description="Number of currently active sessions")
    capacity_limit: Optional[int] = Field(
        default=None, description="Max session capacity if bounded"
    )


class SimulationReadinessResponse(BaseModel):
    """Aggregated health and readiness report across all defense simulation engines."""

    status: str = Field(default="healthy", description="healthy | degraded")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version string")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC server timestamp",
    )
    supported_modes: List[str] = Field(..., description="List of all supported defense modes")
    modes: Dict[str, SimulationModeStatus] = Field(
        ..., description="Per-mode operational status and session counts"
    )
    total_active_simulations: int = Field(
        ..., description="Sum of active sessions across all simulation stores"
    )
