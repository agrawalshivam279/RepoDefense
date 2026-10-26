import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChunkType(str, Enum):
    """Classification of code chunk origin and structural role."""

    SYMBOL = "symbol"
    MODULE_HEADER = "header"
    BLOCK = "block"
    FALLBACK = "fallback"


class CodeChunk(BaseModel):
    """Self-contained, AST-grounded code chunk for vectorization and retrieval."""

    file_id: uuid.UUID = Field(..., description="Parent AnalyzedFile UUID")
    symbol_id: Optional[uuid.UUID] = Field(None, description="Linked CodeSymbol UUID if applicable")
    symbol_name: Optional[str] = Field(None, description="Name of the enclosing symbol")
    chunk_type: ChunkType = Field(..., description="Structural classification of the chunk")
    content: str = Field(..., description="Exact code text slice")
    start_line: int = Field(..., ge=1, description="1-indexed starting line")
    end_line: int = Field(..., ge=1, description="1-indexed ending line")
    token_count: int = Field(..., ge=1, description="Estimated token count")
    language: str = Field(..., description="Programming language tag")

    model_config = ConfigDict(from_attributes=True)
