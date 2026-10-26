from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class SymbolMetadata(BaseModel):
    """Deterministic structural metadata extracted for an AST code symbol."""

    name: str = Field(description="Symbol identifier name")
    symbol_type: str = Field(
        description="Classification: function, async_function, class, method, or endpoint"
    )
    start_line: int = Field(ge=1, description="1-indexed starting line number")
    end_line: int = Field(ge=1, description="1-indexed ending line number")
    signature: Optional[str] = Field(
        default=None,
        description="Normalized callable signature or class declaration",
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Extracted docstring text if available",
    )
    decorators: list[str] = Field(
        default_factory=list,
        description="List of decorator strings decorating the symbol",
    )


class BaseASTParser(ABC):
    """Abstract base class for language-specific Tree-sitter AST parsers."""

    @abstractmethod
    def parse(self, code_bytes: bytes) -> list[SymbolMetadata]:
        """Parses raw source code bytes into a list of SymbolMetadata.

        Args:
            code_bytes: UTF-8 encoded source file bytes.

        Returns:
            List of SymbolMetadata sorted by starting line number.
        """
        raise NotImplementedError
