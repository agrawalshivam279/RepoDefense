"""Service for synthesizing holistic, enhanced architectural defense reports."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.report_generator import generate_defense_report
from app.models.project import Project
from app.schemas.defense import DefenseSessionState
from app.schemas.report import EnhancedDefenseReportResponse
from app.services.architecture import detect_repository_architecture
from app.services.diagram import generate_project_architecture_diagram
from app.services.tech_audit import audit_project_technology

logger = structlog.get_logger(__name__)


async def generate_enhanced_defense_report(
    session: DefenseSessionState,
    db: AsyncSession,
) -> EnhancedDefenseReportResponse:
    """Generates an enhanced defense report combining interview rubrics with repo ground truth."""
    # 1. Generate base Principal Engineer defense evaluation
    base_report = await generate_defense_report(session)

    # 2. Retrieve project record for auxiliary architectural diagnostics
    project_uuid = uuid.UUID(session.project_id)
    stmt = select(Project).where(Project.id == project_uuid)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    arch_pattern: str | None = None
    arch_tier: str | None = None
    diagram_code: str | None = None
    tech_score: int | None = None
    tech_flagged: int | None = None
    tech_total: int | None = None

    if project:
        # A. Safely fetch detected architectural pattern
        try:
            arch_report = await detect_repository_architecture(project, db)
            arch_pattern = arch_report.primary_pattern.pattern_name
            arch_tier = arch_report.primary_pattern.tier.value
        except Exception as exc:
            logger.warning(
                "enhanced_report_arch_detection_skipped",
                project_id=str(project_uuid),
                error=str(exc),
            )

        # B. Safely fetch Mermaid architecture diagram
        try:
            diag = await generate_project_architecture_diagram(project, db)
            diagram_code = diag.mermaid_code
        except Exception as exc:
            logger.warning(
                "enhanced_report_diagram_skipped",
                project_id=str(project_uuid),
                error=str(exc),
            )

        # C. Safely fetch technology & dependency health audit
        try:
            tech_audit = await audit_project_technology(project, db)
            tech_score = tech_audit.tech_health_score
            tech_flagged = tech_audit.flagged_dependencies_count
            tech_total = tech_audit.total_dependencies_audited
        except Exception as exc:
            logger.warning(
                "enhanced_report_tech_audit_skipped",
                project_id=str(project_uuid),
                error=str(exc),
            )

    logger.info(
        "enhanced_defense_report_synthesized",
        session_id=str(session.session_id),
        project_id=str(session.project_id),
        has_arch=bool(arch_pattern),
        has_diagram=bool(diagram_code),
        tech_score=tech_score,
    )

    return EnhancedDefenseReportResponse(
        session_id=base_report.session_id,
        project_id=base_report.project_id,
        overall_score=base_report.overall_score,
        verdict=base_report.verdict,
        summary=base_report.summary,
        category_scores=base_report.category_scores,
        key_strengths=base_report.key_strengths,
        critical_blind_spots=base_report.critical_blind_spots,
        actionable_recommendations=base_report.actionable_recommendations,
        total_questions=base_report.total_questions,
        completed_at=base_report.completed_at,
        architecture_primary_pattern=arch_pattern,
        architecture_confidence_tier=arch_tier,
        diagram_mermaid_code=diagram_code,
        tech_health_score=tech_score,
        tech_flagged_count=tech_flagged,
        tech_total_dependencies=tech_total,
        claims_verified_count=None,
        claims_total_count=None,
    )
