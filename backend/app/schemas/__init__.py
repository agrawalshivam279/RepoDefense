"""Pydantic schemas and data contracts."""

from app.schemas.chunk import (
    ChunkType,
    CodeChunk,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
    DefenseTurn,
    EvaluationOutput,
    SecondaryEvaluationOutput,
    StartDefenseRequest,
    SubmitAnswerRequest,
    TurnRole,
)
from app.schemas.embedding import (
    RetrievalQuery,
    RetrievedChunk,
)
from app.schemas.evidence import (
    EvidenceBase,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceType,
)
from app.schemas.question import (
    EvidenceRef,
    GroundedQuestion,
    QuestionCategory,
    QuestionGenerationInput,
    QuestionGenerationResponse,
)
from app.schemas.report import (
    CategoryScore,
    DefenseReportResponse,
    ReportSynthesisOutput,
)
from app.schemas.summary import (
    ProjectSummary,
    ProjectSummaryInput,
)

__all__ = [
    "CategoryScore",
    "ChunkType",
    "CodeChunk",
    "DefenseQuestionProgress",
    "DefenseReportResponse",
    "DefenseSessionState",
    "DefenseStage",
    "DefenseTurn",
    "EvaluationOutput",
    "EvidenceBase",
    "EvidenceCreate",
    "EvidenceRef",
    "EvidenceResponse",
    "EvidenceType",
    "GroundedQuestion",
    "ProjectSummary",
    "ProjectSummaryInput",
    "QuestionCategory",
    "QuestionGenerationInput",
    "QuestionGenerationResponse",
    "ReportSynthesisOutput",
    "RetrievalQuery",
    "RetrievedChunk",
    "SecondaryEvaluationOutput",
    "StartDefenseRequest",
    "SubmitAnswerRequest",
    "TurnRole",
]
