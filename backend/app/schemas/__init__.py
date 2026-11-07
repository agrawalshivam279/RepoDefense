"""Pydantic schemas and data contracts."""

from app.schemas.architecture import (
    ArchitecturalRisk,
    ArchitecturePatternType,
    ArchitectureReportResponse,
    DetectedPattern,
    PatternConfidenceTier,
    PatternIndicator,
)
from app.schemas.chunk import (
    ChunkType,
    CodeChunk,
)
from app.schemas.claim import (
    ClaimCategory,
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    TechnicalClaim,
)
from app.schemas.claim_verification import (
    BatchClaimVerificationResponse,
    ClaimVerificationRequest,
    ClaimVerificationResult,
    EvidenceCitation,
    VerificationStatus,
)
from app.schemas.coverage import (
    BlindSpotItem,
    CoverageStatus,
    CoverageTier,
    FileCoverageItem,
    ModuleCoverageItem,
    ProjectCoverageResponse,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
    DefenseTurn,
    DifficultyLevel,
    EvaluationOutput,
    SecondaryEvaluationOutput,
    StartDefenseRequest,
    SubmitAnswerRequest,
    TurnRole,
)
from app.schemas.diagram import (
    DiagramEdge,
    DiagramNode,
    DiagramResponse,
    DiagramType,
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
from app.schemas.ownership import (
    AuthorShare,
    FileOwnershipSummary,
    OwnershipStatus,
    ProjectOwnershipReport,
    SymbolOwnership,
)
from app.schemas.project import (
    DependencyOverviewItem,
    LanguageMetric,
    ProjectCreate,
    ProjectOverviewResponse,
    ProjectResponse,
    RepositoryOverviewMetrics,
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
    EnhancedDefenseReportResponse,
    ReportSynthesisOutput,
)
from app.schemas.summary import (
    ProjectSummary,
    ProjectSummaryInput,
)
from app.schemas.tech_audit import (
    AuditCategory,
    AuditedDependencyItem,
    AuditSeverity,
    TechAuditReportResponse,
)

__all__ = [
    "ArchitecturalRisk",
    "ArchitecturePatternType",
    "ArchitectureReportResponse",
    "AuthorShare",
    "BatchClaimVerificationResponse",
    "BlindSpotItem",
    "CategoryScore",
    "ChunkType",
    "ClaimCategory",
    "ClaimExtractionRequest",
    "ClaimExtractionResponse",
    "ClaimVerificationRequest",
    "ClaimVerificationResult",
    "CodeChunk",
    "CoverageStatus",
    "CoverageTier",
    "DefenseQuestionProgress",
    "DefenseReportResponse",
    "EnhancedDefenseReportResponse",
    "DefenseSessionState",
    "DefenseStage",
    "DefenseTurn",
    "DiagramEdge",
    "DiagramNode",
    "DiagramResponse",
    "DiagramType",
    "DependencyOverviewItem",
    "DetectedPattern",
    "DifficultyLevel",
    "EvaluationOutput",
    "EvidenceBase",
    "EvidenceCitation",
    "EvidenceCreate",
    "EvidenceRef",
    "EvidenceResponse",
    "EvidenceType",
    "FileCoverageItem",
    "FileOwnershipSummary",
    "GroundedQuestion",
    "LanguageMetric",
    "ModuleCoverageItem",
    "OwnershipStatus",
    "PatternConfidenceTier",
    "PatternIndicator",
    "ProjectCoverageResponse",
    "ProjectCreate",
    "ProjectOverviewResponse",
    "ProjectOwnershipReport",
    "ProjectResponse",
    "ProjectSummary",
    "ProjectSummaryInput",
    "QuestionCategory",
    "QuestionGenerationInput",
    "QuestionGenerationResponse",
    "ReportSynthesisOutput",
    "RepositoryOverviewMetrics",
    "RetrievalQuery",
    "RetrievedChunk",
    "SecondaryEvaluationOutput",
    "StartDefenseRequest",
    "SubmitAnswerRequest",
    "SymbolOwnership",
    "TechnicalClaim",
    "AuditCategory",
    "AuditSeverity",
    "AuditedDependencyItem",
    "TechAuditReportResponse",
    "TurnRole",
    "VerificationStatus",
]
