"""Pydantic v2 data contracts for repository defense coverage tracking."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CoverageStatus(str, Enum):
    """Categorical status for a file or directory module's defense coverage."""

    TESTED = "tested"
    PARTIAL = "partial"
    UNTESTED = "untested"


class CoverageTier(str, Enum):
    """Executive assessment tier of total repository defense depth."""

    NEEDS_DEFENSE = "Needs More Defense"
    SUBSTANTIAL = "Substantial Coverage"
    PRINCIPAL_VERIFIED = "Principal Verified"


class FileCoverageItem(BaseModel):
    """Detailed defense coverage metrics for a single repository file."""

    file_path: str = Field(..., description="POSIX relative path from repository root.")
    language: str = Field(..., description="Classified programming or markup language.")
    total_lines: int = Field(default=0, ge=0, description="Total physical lines of code.")
    is_tested: bool = Field(default=False, description="Whether this file was cited in defenses.")
    test_count: int = Field(default=0, ge=0, description="Total questions citing this file.")
    associated_evidence_count: int = Field(
        default=0, ge=0, description="Total architectural evidence records located in this file."
    )
    tested_evidence_count: int = Field(
        default=0, ge=0, description="Count of evidence items tested in defense questions."
    )
    average_score: Optional[float] = Field(
        default=None, description="Average defense score (1.0-10.0) across citing questions."
    )
    highest_difficulty: Optional[str] = Field(
        default=None, description="Highest difficulty level at which this file was defended."
    )


class ModuleCoverageItem(BaseModel):
    """Aggregated coverage metrics for a top-level or architectural directory module."""

    module_path: str = Field(..., description="Directory or module prefix (e.g. backend/app).")
    total_files: int = Field(default=0, ge=0, description="Total cataloged files in this module.")
    tested_files: int = Field(default=0, ge=0, description="Count of files tested in defenses.")
    coverage_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Percentage of files defended in this module."
    )
    status: CoverageStatus = Field(
        default=CoverageStatus.UNTESTED, description="Status classification."
    )


class BlindSpotItem(BaseModel):
    """High-priority untested architectural evidence requiring candidate interrogation."""

    file_path: str = Field(..., description="File path containing the untested evidence.")
    evidence_id: str = Field(..., description="UUID identifier of the evidence record.")
    evidence_type: str = Field(..., description="Architectural type (e.g. database, auth, queue).")
    title: str = Field(..., description="Descriptive title of the load-bearing component.")
    description: str = Field(..., description="Summary of why this component is critical.")
    start_line: int = Field(..., ge=1, description="1-indexed starting line.")
    end_line: int = Field(..., ge=1, description="1-indexed ending line.")
    priority: str = Field(
        default="medium", description="Heuristic importance rating (critical, high, medium)."
    )


class ProjectCoverageResponse(BaseModel):
    """Comprehensive repository coverage report payload."""

    project_id: str = Field(..., description="UUID of the analyzed project.")
    project_name: str = Field(..., description="Name of the repository.")
    total_files: int = Field(default=0, ge=0, description="Total cataloged source files.")
    tested_files_count: int = Field(default=0, ge=0, description="Count of defended files.")
    untested_files_count: int = Field(default=0, ge=0, description="Count of untested files.")
    file_coverage_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Ratio of tested files to total files."
    )
    total_evidence_items: int = Field(default=0, ge=0, description="Total architectural evidence.")
    tested_evidence_count: int = Field(default=0, ge=0, description="Tested evidence items.")
    evidence_coverage_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Ratio of tested evidence to total evidence."
    )
    total_lines_covered: int = Field(
        default=0, ge=0, description="Sum of physical lines in tested files."
    )
    overall_coverage_tier: CoverageTier = Field(
        default=CoverageTier.NEEDS_DEFENSE, description="Executive rating tier."
    )
    modules: List[ModuleCoverageItem] = Field(
        default_factory=list, description="Directory module heatmap items."
    )
    files: List[FileCoverageItem] = Field(
        default_factory=list, description="Per-file detailed defense metrics."
    )
    blind_spots: List[BlindSpotItem] = Field(
        default_factory=list, description="Ranked list of untested critical components."
    )
