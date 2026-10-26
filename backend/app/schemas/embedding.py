import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RetrievalQuery(BaseModel):
    """Query parameters for semantic code retrieval via pgvector."""

    model_config = ConfigDict(frozen=True)

    project_id: uuid.UUID
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    file_id: Optional[uuid.UUID] = None


class RetrievedChunk(BaseModel):
    """A code chunk retrieved via pgvector cosine distance search."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    file_path: str
    symbol_id: Optional[uuid.UUID] = None
    chunk_content: str
    similarity: float = Field(ge=0.0, le=1.0)
    token_count: int
