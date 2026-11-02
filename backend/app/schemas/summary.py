from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ProjectSummary(BaseModel):
    """Structured architectural overview of a repository synthesized by AI."""

    title: str = Field(..., description="Concise descriptive title of the repository/system")
    tagline: str = Field(..., description="One-line pitch explaining what the repository does")
    primary_language: str = Field(..., description="Dominant language of the codebase")
    detected_frameworks: List[str] = Field(
        default_factory=list, description="Primary web frameworks and core libraries identified"
    )
    architectural_style: str = Field(
        ...,
        description="Architectural style (e.g. Modular Monolith, Microservices, SPA + API)",
    )
    key_components: List[str] = Field(
        default_factory=list, description="Key functional components or modules identified"
    )
    potential_defense_topics: List[str] = Field(
        default_factory=list,
        description="Architectural trade-offs or stress points for candidate defense sessions",
    )
    narrative: str = Field(
        ..., description="2-3 paragraph deep-dive architectural narrative grounded in code evidence"
    )

    model_config = ConfigDict(extra="ignore")


class ProjectSummaryInput(BaseModel):
    """Consolidated repository metadata fed into the summary generation prompt."""

    project_name: str = Field(..., description="Project / repository display name")
    commit_hash: str = Field(..., description="Git commit hash (short or full SHA)")
    total_files: int = Field(0, description="Total number of scanned source files")
    total_lines: int = Field(0, description="Total lines of code scanned")
    top_languages: List[str] = Field(
        default_factory=list, description="Top languages with file counts"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Sample of primary runtime packages and libraries"
    )
    evidence_tags: List[str] = Field(
        default_factory=list, description="Deterministic architectural evidence labels extracted"
    )
    top_contributors: List[str] = Field(
        default_factory=list, description="Top git contributors by commit activity"
    )

    model_config = ConfigDict(extra="ignore")
