"""Cross-mode candidate performance analytics and repository telemetry aggregation."""

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import DefenseSessionStore, defense_store
from app.models.analysis import AnalyzedFile
from app.models.project import Project, RepositorySnapshot
from app.schemas.analytics import (
    CategorySkillMetric,
    DefenseModeKey,
    LanguageDistributionItem,
    ModePerformanceMetric,
    ModuleCoveragePoint,
    ProjectAnalyticsResponse,
    ScoreTrendPoint,
    WorkspaceAnalyticsSummary,
)
from app.services.analytics_extractors import (
    MODE_LABELS,
    SessionSample,
    collect_samples_for_projects,
)
from app.services.coverage import calculate_project_coverage
from app.services.tech_audit import audit_project_technology

logger = structlog.get_logger(__name__)
PASS_THRESHOLD_PCT = 70.0


def _aggregate_modes(samples: List[SessionSample]) -> List[ModePerformanceMetric]:
    by_mode: Dict[DefenseModeKey, List[SessionSample]] = {m: [] for m in DefenseModeKey}
    for item in samples:
        by_mode[item.mode].append(item)

    metrics: List[ModePerformanceMetric] = []
    for mode in DefenseModeKey:
        group = by_mode[mode]
        completed_scores = [s.score_pct for s in group if s.completed and s.score_pct is not None]
        n_comp = len(completed_scores)
        avg_val = round(sum(completed_scores) / n_comp, 1) if n_comp else None
        best_val = round(max(completed_scores), 1) if n_comp else None
        passed_n = sum(1 for sc in completed_scores if sc >= PASS_THRESHOLD_PCT)
        pass_rate = round((passed_n / n_comp) * 100.0, 1) if n_comp else None
        metrics.append(
            ModePerformanceMetric(
                mode=mode,
                label=MODE_LABELS[mode],
                sessions_total=len(group),
                sessions_completed=sum(1 for s in group if s.completed),
                avg_score_pct=avg_val,
                best_score_pct=best_val,
                pass_rate_pct=pass_rate,
            )
        )
    return metrics


def _aggregate_skills(samples: List[SessionSample]) -> List[CategorySkillMetric]:
    totals: Dict[str, List[float]] = {}
    for sample in samples:
        for cat, val in sample.skills.items():
            totals.setdefault(cat, []).append(val)
    result = [
        CategorySkillMetric(
            category=cat,
            confidence_pct=round(sum(vals) / len(vals), 1),
            evaluations_count=len(vals),
        )
        for cat, vals in totals.items()
    ]
    result.sort(key=lambda r: (-r.confidence_pct, r.category))
    return result


def _build_trend(samples: List[SessionSample], limit: int = 25) -> List[ScoreTrendPoint]:
    scored = [
        ScoreTrendPoint(
            session_id=s.session_id,
            mode=s.mode,
            label=MODE_LABELS[s.mode],
            score_pct=s.score_pct,
            timestamp=s.timestamp,
            topic_or_title=s.topic_or_title,
        )
        for s in samples
        if s.completed and s.score_pct is not None
    ]
    scored.sort(key=lambda pt: pt.timestamp)
    return scored[-limit:]


async def _fetch_language_distribution(
    project_id: uuid.UUID, db: AsyncSession
) -> List[LanguageDistributionItem]:
    snap_stmt = (
        select(RepositorySnapshot.id)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snap_id = (await db.execute(snap_stmt)).scalars().first()
    if not snap_id:
        return []

    lang_stmt = (
        select(
            AnalyzedFile.language,
            func.count(AnalyzedFile.id).label("file_count"),
            func.coalesce(func.sum(AnalyzedFile.total_lines), 0).label("total_lines"),
        )
        .where(AnalyzedFile.snapshot_id == snap_id)
        .group_by(AnalyzedFile.language)
        .order_by(func.sum(AnalyzedFile.total_lines).desc())
    )
    rows = (await db.execute(lang_stmt)).all()
    grand_lines = sum(int(r.total_lines or 0) for r in rows)
    return [
        LanguageDistributionItem(
            language=str(r.language or "unknown"),
            file_count=int(r.file_count or 0),
            total_lines=int(r.total_lines or 0),
            line_share_pct=(
                round((int(r.total_lines or 0) / grand_lines) * 100.0, 1)
                if grand_lines > 0
                else 0.0
            ),
        )
        for r in rows
    ]


async def build_project_analytics(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    fsm_store: Optional[DefenseSessionStore] = None,
    stress_store: Optional[Dict[str, Any]] = None,
    incident_store: Optional[Dict[Any, Any]] = None,
    arch_store: Optional[Dict[str, Any]] = None,
) -> ProjectAnalyticsResponse:
    """Computes cross-mode performance analytics and codebase metrics for a user project."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    target_fsm = fsm_store if fsm_store is not None else defense_store
    samples = await collect_samples_for_projects(
        {str(project.id)},
        fsm_store=target_fsm,
        stress_store=stress_store,
        incident_store=incident_store,
        arch_store=arch_store,
    )
    completed_scores = [s.score_pct for s in samples if s.completed and s.score_pct is not None]
    n_comp = len(completed_scores)
    readiness = round(sum(completed_scores) / n_comp, 1) if n_comp else None

    file_cov_pct: Optional[float] = None
    ev_cov_pct: Optional[float] = None
    module_points: List[ModuleCoveragePoint] = []
    try:
        cov = await calculate_project_coverage(project.id, user_id, db, store=target_fsm)
        file_cov_pct = cov.file_coverage_percentage
        ev_cov_pct = cov.evidence_coverage_percentage
        module_points = [
            ModuleCoveragePoint(
                module_path=m.module_path,
                coverage_pct=m.coverage_percentage,
                tested_files=m.tested_files,
                total_files=m.total_files,
            )
            for m in cov.modules
        ]
    except Exception as exc:
        logger.warning("analytics_coverage_skipped", project_id=str(project.id), error=str(exc))

    tech_score: Optional[int] = None
    try:
        tech_report = await audit_project_technology(project, db)
        tech_score = tech_report.tech_health_score
    except Exception as exc:
        logger.warning("analytics_tech_audit_skipped", project_id=str(project.id), error=str(exc))

    languages = await _fetch_language_distribution(project.id, db)

    return ProjectAnalyticsResponse(
        project_id=str(project.id),
        project_name=project.name,
        overall_readiness_pct=readiness,
        total_sessions=len(samples),
        completed_sessions=sum(1 for s in samples if s.completed),
        file_coverage_pct=file_cov_pct,
        evidence_coverage_pct=ev_cov_pct,
        tech_health_score=tech_score,
        mode_breakdown=_aggregate_modes(samples),
        category_skills=_aggregate_skills(samples),
        score_trend=_build_trend(samples),
        language_distribution=languages,
        module_coverage=module_points,
    )


async def build_workspace_analytics(
    user_id: uuid.UUID,
    db: AsyncSession,
    fsm_store: Optional[DefenseSessionStore] = None,
    stress_store: Optional[Dict[str, Any]] = None,
    incident_store: Optional[Dict[Any, Any]] = None,
    arch_store: Optional[Dict[str, Any]] = None,
) -> WorkspaceAnalyticsSummary:
    """Computes aggregated performance analytics across all repositories owned by a user."""
    proj_stmt = select(Project).where(Project.user_id == user_id)
    projects = list((await db.execute(proj_stmt)).scalars().all())
    allowed_ids = {str(p.id) for p in projects}

    samples = await collect_samples_for_projects(
        allowed_ids,
        fsm_store=fsm_store,
        stress_store=stress_store,
        incident_store=incident_store,
        arch_store=arch_store,
    )
    completed_scores = [s.score_pct for s in samples if s.completed and s.score_pct is not None]
    n_comp = len(completed_scores)
    avg_readiness = round(sum(completed_scores) / n_comp, 1) if n_comp else None
    analyzed_count = sum(1 for p in projects if str(p.status) == "analyzed")

    return WorkspaceAnalyticsSummary(
        total_projects=len(projects),
        analyzed_projects=analyzed_count,
        total_sessions=len(samples),
        completed_sessions=sum(1 for s in samples if s.completed),
        avg_readiness_pct=avg_readiness,
        mode_breakdown=_aggregate_modes(samples),
        recent_trend=_build_trend(samples, limit=20),
    )
