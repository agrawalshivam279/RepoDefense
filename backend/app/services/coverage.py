"""Service calculating repository defense coverage, module heatmaps, and untested blind spots."""

import posixpath
import uuid
from typing import Dict, List, Optional, Set

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import DefenseSessionStore, defense_store
from app.models.analysis import AnalyzedFile, Evidence
from app.models.project import Project, RepositorySnapshot
from app.schemas.coverage import (
    BlindSpotItem,
    CoverageStatus,
    CoverageTier,
    FileCoverageItem,
    ModuleCoverageItem,
    ProjectCoverageResponse,
)
from app.schemas.defense import DefenseStage


def _resolve_module_path(file_path: str) -> str:
    """Extracts a standardized 1-2 level directory module key from a file path."""
    clean_path = file_path.strip().replace("\\", "/")
    dirname = posixpath.dirname(clean_path)
    if not dirname or dirname == ".":
        return "root"
    parts = dirname.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]


def _classify_evidence_priority(evidence_type: str) -> str:
    """Heuristically ranks evidence importance for untested blind spots."""
    ev_lower = evidence_type.lower()
    if any(k in ev_lower for k in ["database", "auth", "queue", "security"]):
        return "critical"
    if any(k in ev_lower for k in ["api_endpoint", "endpoint", "framework"]):
        return "high"
    return "medium"


async def calculate_project_coverage(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    store: Optional[DefenseSessionStore] = None,
) -> ProjectCoverageResponse:
    """Computes comprehensive repository defense coverage metrics."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access project coverage.")

    stmt_snap = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snap_res = await db.execute(stmt_snap)
    snapshot = snap_res.scalars().first()

    analyzed_files: List[AnalyzedFile] = []
    if snapshot:
        stmt_files = (
            select(AnalyzedFile)
            .where(AnalyzedFile.snapshot_id == snapshot.id)
            .order_by(AnalyzedFile.path.asc())
        )
        files_res = await db.execute(stmt_files)
        analyzed_files = list(files_res.scalars().all())

    stmt_ev = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .order_by(Evidence.file_path.asc())
    )
    ev_res = await db.execute(stmt_ev)
    evidence_list = list(ev_res.scalars().all())

    target_store = store or defense_store
    sessions = await target_store.get_by_project(str(project_id))

    tested_file_counts: Dict[str, int] = {}
    tested_file_scores: Dict[str, List[float]] = {}
    tested_file_difficulties: Dict[str, Set[str]] = {}
    tested_evidence_ids: Set[str] = set()

    diff_rank = {"foundational": 1, "intermediate": 2, "advanced": 3}

    for s in sessions:
        for prog in s.questions:
            is_active_or_done = prog.initial_defense is not None or prog.status in (
                DefenseStage.STRESS_TEST_ACTIVE,
                DefenseStage.MENTOR_ACTIVE,
                DefenseStage.PUSHBACK_ACTIVE,
                DefenseStage.QUESTION_COMPLETED,
            )
            if not is_active_or_done:
                continue

            for ev_id in prog.question.cited_evidence_ids:
                tested_evidence_ids.add(str(ev_id))

            q_score = (
                float(prog.final_score)
                if prog.final_score is not None
                else (float(prog.defense_score) if prog.defense_score is not None else None)
            )
            diff_val = (
                prog.difficulty.value
                if hasattr(prog.difficulty, "value")
                else str(prog.difficulty)
            )

            for fp in prog.question.cited_files:
                clean_fp = fp.strip().replace("\\", "/")
                tested_file_counts[clean_fp] = tested_file_counts.get(clean_fp, 0) + 1
                if q_score is not None:
                    tested_file_scores.setdefault(clean_fp, []).append(q_score)
                tested_file_difficulties.setdefault(clean_fp, set()).add(diff_val)

    file_items: List[FileCoverageItem] = []
    modules_map: Dict[str, List[FileCoverageItem]] = {}
    total_lines_covered = 0

    for af in analyzed_files:
        norm_path = af.path.strip().replace("\\", "/")
        matched_ev = [
            ev for ev in evidence_list
            if ev.file_path.strip().replace("\\", "/") == norm_path
        ]
        tested_ev_count = sum(1 for ev in matched_ev if str(ev.id) in tested_evidence_ids)

        test_count = tested_file_counts.get(norm_path, 0)
        is_tested = test_count > 0 or tested_ev_count > 0

        scores = tested_file_scores.get(norm_path, [])
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        diffs = tested_file_difficulties.get(norm_path, set())
        highest_diff = max(diffs, key=lambda d: diff_rank.get(d.lower(), 0)) if diffs else None

        if is_tested:
            total_lines_covered += af.total_lines

        item = FileCoverageItem(
            file_path=norm_path,
            language=af.language,
            total_lines=af.total_lines,
            is_tested=is_tested,
            test_count=test_count,
            associated_evidence_count=len(matched_ev),
            tested_evidence_count=tested_ev_count,
            average_score=avg_score,
            highest_difficulty=highest_diff,
        )
        file_items.append(item)

        mod_key = _resolve_module_path(norm_path)
        modules_map.setdefault(mod_key, []).append(item)

    module_items: List[ModuleCoverageItem] = []
    for mod_path in sorted(modules_map.keys()):
        files_in_mod = modules_map[mod_path]
        mod_total = len(files_in_mod)
        mod_tested = sum(1 for f in files_in_mod if f.is_tested)
        cov_pct = round((mod_tested / mod_total) * 100, 1) if mod_total > 0 else 0.0

        if cov_pct == 100.0:
            status = CoverageStatus.TESTED
        elif cov_pct > 0.0:
            status = CoverageStatus.PARTIAL
        else:
            status = CoverageStatus.UNTESTED

        module_items.append(
            ModuleCoverageItem(
                module_path=mod_path,
                total_files=mod_total,
                tested_files=mod_tested,
                coverage_percentage=cov_pct,
                status=status,
            )
        )

    blind_spots: List[BlindSpotItem] = []
    for ev in evidence_list:
        ev_file = ev.file_path.strip().replace("\\", "/")
        is_ev_tested = str(ev.id) in tested_evidence_ids or tested_file_counts.get(ev_file, 0) > 0
        if not is_ev_tested:
            blind_spots.append(
                BlindSpotItem(
                    file_path=ev_file,
                    evidence_id=str(ev.id),
                    evidence_type=ev.evidence_type,
                    title=ev.title,
                    description=ev.description,
                    start_line=ev.start_line,
                    end_line=ev.end_line,
                    priority=_classify_evidence_priority(ev.evidence_type),
                )
            )

    priority_weight = {"critical": 0, "high": 1, "medium": 2}
    blind_spots.sort(key=lambda b: (priority_weight.get(b.priority, 9), b.file_path))

    total_files = len(analyzed_files)
    tested_files_count = sum(1 for f in file_items if f.is_tested)
    untested_files_count = total_files - tested_files_count
    file_cov_pct = round((tested_files_count / total_files) * 100, 1) if total_files > 0 else 0.0

    total_ev = len(evidence_list)
    tested_ev_total = sum(1 for ev in evidence_list if str(ev.id) in tested_evidence_ids)
    ev_cov_pct = round((tested_ev_total / total_ev) * 100, 1) if total_ev > 0 else 0.0

    if file_cov_pct >= 80.0:
        overall_tier = CoverageTier.PRINCIPAL_VERIFIED
    elif file_cov_pct >= 40.0:
        overall_tier = CoverageTier.SUBSTANTIAL
    else:
        overall_tier = CoverageTier.NEEDS_DEFENSE

    return ProjectCoverageResponse(
        project_id=str(project.id),
        project_name=project.name,
        total_files=total_files,
        tested_files_count=tested_files_count,
        untested_files_count=untested_files_count,
        file_coverage_percentage=file_cov_pct,
        total_evidence_items=total_ev,
        tested_evidence_count=tested_ev_total,
        evidence_coverage_percentage=ev_cov_pct,
        total_lines_covered=total_lines_covered,
        overall_coverage_tier=overall_tier,
        modules=module_items,
        files=file_items,
        blind_spots=blind_spots,
    )
