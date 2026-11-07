from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.architecture import (
    detect_architectural_risks,
    eval_clean_architecture,
    eval_event_driven,
    eval_layered_architecture,
    eval_modular_monolith,
    eval_mvc,
    normalize_directory_tokens,
)
from app.models.analysis import AnalyzedFile, Dependency, Evidence
from app.models.project import Project, RepositorySnapshot
from app.schemas.architecture import (
    ArchitecturePatternType,
    ArchitectureReportResponse,
    DetectedPattern,
    PatternConfidenceTier,
)


async def detect_repository_architecture(
    project: Project, db: AsyncSession
) -> ArchitectureReportResponse:
    """Analyze directory topology, dependencies, and evidence to classify architecture."""
    # 1. Fetch latest snapshot
    snap_stmt = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snap_res = await db.execute(snap_stmt)
    snapshot = snap_res.scalar_one_or_none()

    file_paths: list[str] = []
    if snapshot:
        files_stmt = select(AnalyzedFile.path).where(AnalyzedFile.snapshot_id == snapshot.id)
        files_res = await db.execute(files_stmt)
        file_paths = [row[0] for row in files_res.all()]

    # 2. Fetch project dependencies
    deps_stmt = select(Dependency.name).where(Dependency.project_id == project.id)
    deps_res = await db.execute(deps_stmt)
    deps = {row[0].lower().strip() for row in deps_res.all()}

    # 3. Fetch project evidence types
    ev_stmt = select(Evidence.evidence_type).where(Evidence.project_id == project.id)
    ev_res = await db.execute(ev_stmt)
    evidence_types = {str(row[0]).lower().strip() for row in ev_res.all()}

    # 4. Tokenize directories
    dir_counts, top_dirs = normalize_directory_tokens(file_paths)

    # 5. Evaluate all patterns
    patterns: list[DetectedPattern] = [
        eval_modular_monolith(top_dirs, dir_counts, deps),
        eval_mvc(dir_counts, deps),
        eval_clean_architecture(dir_counts),
        eval_event_driven(dir_counts, deps, evidence_types),
        eval_layered_architecture(dir_counts),
    ]

    patterns.sort(key=lambda p: p.confidence_score, reverse=True)
    top_pattern = patterns[0]

    if top_pattern.confidence_score >= 0.40:
        primary = top_pattern
        secondary = [p for p in patterns[1:] if p.confidence_score >= 0.45]
    else:
        primary = DetectedPattern(
            pattern_type=ArchitecturePatternType.UNSTRUCTURED,
            pattern_name="Unstructured / Ad-Hoc Script",
            confidence_score=0.20,
            tier=PatternConfidenceTier.LOW,
            summary="Minimal modular boundaries or conventional architectural directory patterns.",
            indicators=[],
        )
        secondary = []

    risks = detect_architectural_risks(dir_counts, len(file_paths), deps, evidence_types)

    return ArchitectureReportResponse(
        project_id=str(project.id),
        project_name=project.name,
        primary_pattern=primary,
        secondary_patterns=secondary,
        all_patterns=patterns,
        architectural_risks=risks,
        directory_summary={k: v for k, v in sorted(dir_counts.items())[:15]},
        total_files_analyzed=len(file_paths),
    )
