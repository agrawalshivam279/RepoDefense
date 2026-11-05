"""Pydantic v2 data contracts for repository ownership and author attribution."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class OwnershipStatus(str, Enum):
    """Categorical classification of candidate code attribution."""

    PRIMARY = "primary"
    COLLABORATOR = "collaborator"
    MINOR = "minor"
    UNOWNED = "unowned"


class AuthorShare(BaseModel):
    """Line attribution and contribution metrics for a single author."""

    name: str = Field(..., description="Author display name.")
    email: str = Field(..., description="Normalized author email address.")
    lines_authored: int = Field(default=0, ge=0, description="Total physical lines authored.")
    percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of lines authored in the target unit.",
    )


class SymbolOwnership(BaseModel):
    """Detailed git authorship attribution for an extracted code symbol."""

    symbol_id: str = Field(..., description="UUID or identifier of the CodeSymbol.")
    symbol_name: str = Field(..., description="Identifier name of the function or class.")
    symbol_type: str = Field(..., description="AST type: function, method, class, etc.")
    file_path: str = Field(..., description="Relative file path from repository root.")
    start_line: int = Field(..., ge=1, description="1-indexed start line coordinate.")
    end_line: int = Field(..., ge=1, description="1-indexed end line coordinate.")
    total_lines: int = Field(..., ge=0, description="Total physical line span.")
    primary_author: str = Field(..., description="Author responsible for the majority of lines.")
    candidate_ownership_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Percentage authored by the candidate."
    )
    candidate_status: OwnershipStatus = Field(
        default=OwnershipStatus.UNOWNED, description="Attribution category for candidate."
    )
    authors: List[AuthorShare] = Field(
        default_factory=list, description="Distribution of line ownership across all contributors."
    )
    is_architectural_evidence: bool = Field(
        default=False, description="Whether this symbol hosts critical architectural evidence."
    )
    evidence_type: Optional[str] = Field(
        default=None, description="Architectural category (e.g. database, auth, queue)."
    )


class FileOwnershipSummary(BaseModel):
    """Aggregated git authorship distribution for an entire repository file."""

    file_path: str = Field(..., description="Relative file path from repository root.")
    total_lines: int = Field(default=0, ge=0, description="Total physical lines in file.")
    primary_author: str = Field(..., description="Author responsible for the majority of lines.")
    candidate_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Percentage of file authored by candidate."
    )
    candidate_lines: int = Field(
        default=0, ge=0, description="Number of lines authored by candidate."
    )
    authors: List[AuthorShare] = Field(
        default_factory=list, description="Distribution of authorship across all file contributors."
    )


class ProjectOwnershipReport(BaseModel):
    """Comprehensive repository ownership and code authorship report."""

    project_id: str = Field(..., description="UUID of the analyzed project.")
    project_name: str = Field(..., description="Normalized repository name.")
    candidate_email: str = Field(..., description="Email address matched to the candidate.")
    total_symbols_analyzed: int = Field(
        default=0, ge=0, description="Count of AST code symbols evaluated."
    )
    candidate_authored_symbols: int = Field(
        default=0, ge=0, description="Count of symbols where candidate is primary or collaborator."
    )
    candidate_overall_ownership_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Candidate line share across all cataloged source files.",
    )
    flagged_unowned_symbols: List[SymbolOwnership] = Field(
        default_factory=list,
        description="Critical symbols where candidate attribution is unowned or minor.",
    )
    symbols: List[SymbolOwnership] = Field(
        default_factory=list, description="Symbol-level attribution entries."
    )
    files: List[FileOwnershipSummary] = Field(
        default_factory=list, description="File-level attribution entries."
    )
    top_contributors: List[AuthorShare] = Field(
        default_factory=list, description="Top contributors by physical lines authored."
    )
