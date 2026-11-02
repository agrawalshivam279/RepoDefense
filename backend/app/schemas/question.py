"""Pydantic schemas and data contracts for evidence-grounded question generation."""

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionCategory(str, Enum):
    """Architectural and engineering dimensions evaluated during the interview."""

    ARCHITECTURE = "architecture"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    TRADEOFFS = "tradeoffs"


class EvidenceRef(BaseModel):
    """Reference to an extracted codebase evidence record passed to the question generator."""

    id: str = Field(..., description="Unique evidence record ID")
    evidence_type: str = Field(
        ..., description="Category (framework, database, auth, endpoint, queue, infra)"
    )
    title: str = Field(..., description="Concise evidence label")
    description: str = Field(..., description="Detailed description of the evidence")
    file_path: str = Field(..., description="Repository-relative source file path")
    start_line: int = Field(0, description="1-indexed starting line")
    end_line: int = Field(0, description="1-indexed ending line")

    model_config = ConfigDict(extra="ignore")


class GroundedQuestion(BaseModel):
    """An evidence-grounded technical interview question generated for a specific codebase."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique question identifier",
    )
    category: QuestionCategory = Field(
        ...,
        description="Architectural domain of the question",
    )
    question_text: str = Field(
        ...,
        description="The direct technical question posed to the candidate",
    )
    context_hint: str = Field(
        ...,
        description="Factual repository context anchoring the question in candidate's code",
    )
    cited_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of cited Evidence records",
    )
    cited_files: List[str] = Field(
        default_factory=list,
        description="Repository file paths referenced in the question",
    )

    model_config = ConfigDict(extra="ignore")


class QuestionGenerationInput(BaseModel):
    """Consolidated input passed to LiteLLM for question generation."""

    project_name: str = Field(..., description="Project / repository display name")
    summary_narrative: Optional[str] = Field(
        None, description="High-level architectural narrative from snapshot summary"
    )
    architectural_style: Optional[str] = Field(
        None, description="Identified architectural style (e.g., Modular Monolith)"
    )
    evidence_items: List[EvidenceRef] = Field(
        default_factory=list,
        description="Catalog of load-bearing evidence records extracted from codebase",
    )
    requested_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of questions to synthesize",
    )

    model_config = ConfigDict(extra="ignore")


class QuestionGenerationResponse(BaseModel):
    """API response model for generated questions."""

    project_id: uuid.UUID = Field(..., description="Project identifier")
    project_name: str = Field(..., description="Project name")
    questions: List[GroundedQuestion] = Field(
        default_factory=list, description="List of generated questions"
    )
    total_generated: int = Field(..., description="Number of questions returned")
    grounded_evidence_count: int = Field(
        ..., description="Number of unique evidence items cited across questions"
    )

    model_config = ConfigDict(extra="ignore")
