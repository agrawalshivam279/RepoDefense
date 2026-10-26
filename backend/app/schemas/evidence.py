import uuid
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    """Canonical classification for load-bearing architectural evidence."""

    FRAMEWORK = "framework"
    DATABASE = "database"
    AUTH = "auth"
    API_ENDPOINT = "api_endpoint"
    QUEUE = "queue"
    INFRASTRUCTURE = "infrastructure"
    ARCHITECTURE = "architecture"


class EvidenceBase(BaseModel):
    """Base payload for architectural evidence."""

    evidence_type: EvidenceType = Field(..., description="Classification category")
    title: str = Field(..., max_length=255, description="Concise human-readable evidence title")
    description: str = Field(..., description="Detailed explanation of the architectural significance")
    file_path: str = Field(..., max_length=1000, description="Repository-relative file path")
    start_line: int = Field(..., ge=1, description="1-indexed starting line")
    end_line: int = Field(..., ge=1, description="1-indexed ending line")


class EvidenceCreate(EvidenceBase):
    """Payload for creating a new evidence record."""

    project_id: uuid.UUID = Field(..., description="Owning project UUID")


class EvidenceResponse(EvidenceBase):
    """API response model for an evidence record."""

    id: uuid.UUID = Field(..., description="Unique evidence UUID")
    project_id: uuid.UUID = Field(..., description="Owning project UUID")

    model_config = ConfigDict(from_attributes=True)
