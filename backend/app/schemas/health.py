from datetime import datetime, timezone

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
