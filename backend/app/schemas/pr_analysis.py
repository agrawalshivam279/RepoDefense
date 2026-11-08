"""Pydantic v2 schemas for GitHub Pull Request diff analysis and structured patch data."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FileChangeStatus(str, Enum):
    """Classification of file change in a pull request diff."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    BINARY = "binary"


class DiffLineType(str, Enum):
    """Line classification in a unified diff hunk."""

    ADDITION = "addition"
    DELETION = "deletion"
    CONTEXT = "context"


class ParsedDiffLine(BaseModel):
    """Single line representation within a diff hunk."""

    model_config = ConfigDict(extra="ignore")

    line_type: DiffLineType
    content: str
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None


class ParsedDiffHunk(BaseModel):
    """Individual unified diff hunk containing contiguous changed and context lines."""

    model_config = ConfigDict(extra="ignore")

    old_start: int = Field(..., ge=0)
    old_lines: int = Field(..., ge=0)
    new_start: int = Field(..., ge=0)
    new_lines: int = Field(..., ge=0)
    header: str
    lines: List[ParsedDiffLine] = Field(default_factory=list)
    added_count: int = Field(default=0, ge=0)
    deleted_count: int = Field(default=0, ge=0)


class ParsedFileDiff(BaseModel):
    """Structured representation of all diff changes within a single file."""

    model_config = ConfigDict(extra="ignore")

    old_path: Optional[str] = None
    new_path: str
    status: FileChangeStatus
    hunks: List[ParsedDiffHunk] = Field(default_factory=list)
    total_additions: int = Field(default=0, ge=0)
    total_deletions: int = Field(default=0, ge=0)
    is_binary: bool = False


class PRMetadata(BaseModel):
    """Essential metadata extracted from a GitHub Pull Request."""

    model_config = ConfigDict(extra="ignore")

    pr_number: int
    title: str
    body: Optional[str] = None
    author: str
    base_branch: str
    head_branch: str
    head_sha: str
    state: str = "open"
    html_url: str
    created_at: str


class PRAnalysisRequest(BaseModel):
    """Payload to request ingestion and analysis of a GitHub Pull Request."""

    model_config = ConfigDict(extra="ignore")

    pr_url: str = Field(
        ...,
        description="Public GitHub Pull Request URL (e.g. https://github.com/owner/repo/pull/123)",
        min_length=15,
        max_length=500,
    )


class RawDiffParseRequest(BaseModel):
    """Payload to parse a raw unified diff patch stream directly."""

    model_config = ConfigDict(extra="ignore")

    diff_text: str = Field(
        ...,
        description="Unified diff text stream",
        min_length=1,
        max_length=10_000_000,
    )


class PRAnalysisResponse(BaseModel):
    """Complete structured response of an analyzed GitHub Pull Request."""

    model_config = ConfigDict(extra="ignore")

    metadata: PRMetadata
    files: List[ParsedFileDiff] = Field(default_factory=list)
    total_files_changed: int = Field(..., ge=0)
    total_additions: int = Field(..., ge=0)
    total_deletions: int = Field(..., ge=0)
    summary_narrative: str
