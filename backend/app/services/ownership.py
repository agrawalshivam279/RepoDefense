"""Service calculating repository symbol-level and file-level code ownership attribution."""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.blame import LineBlameInfo, compute_range_attribution, parse_file_blame
from app.models.analysis import AnalyzedFile, CodeSymbol, Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.ownership import (
    AuthorShare,
    FileOwnershipSummary,
    OwnershipStatus,
    ProjectOwnershipReport,
    SymbolOwnership,
)


async def calculate_project_ownership(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    candidate_email: Optional[str] = None,
    repo_dir: Optional[Path] = None,
) -> ProjectOwnershipReport:
    """Calculates comprehensive git ownership metrics across symbols and files for a project.

    Args:
        project_id: UUID of the target repository project.
        user_id: UUID of the authenticated user.
        db: Active asynchronous SQLAlchemy session.
        candidate_email: Optional override email for candidate attribution.
        repo_dir: Optional path to the cloned repository on the local filesystem.

    Returns:
        ProjectOwnershipReport payload.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access project ownership.")

    # Determine effective candidate email
    effective_email = candidate_email.strip().lower() if candidate_email else ""
    if not effective_email:
        user = await db.get(User, user_id)
        if user and user.email:
            effective_email = user.email.strip().lower()

    stmt_snap = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snap_res = await db.execute(stmt_snap)
    snapshot = snap_res.scalars().first()

    if not snapshot:
        return ProjectOwnershipReport(
            project_id=str(project_id),
            project_name=project.name,
            candidate_email=effective_email,
            total_symbols_analyzed=0,
            candidate_authored_symbols=0,
            candidate_overall_ownership_percentage=0.0,
        )

    # 1. Fetch AnalyzedFiles
    stmt_files = (
        select(AnalyzedFile)
        .where(AnalyzedFile.snapshot_id == snapshot.id)
        .order_by(AnalyzedFile.path.asc())
    )
    analyzed_files = list((await db.execute(stmt_files)).scalars().all())

    # 2. Fetch CodeSymbols
    file_ids = [f.id for f in analyzed_files]
    symbols: List[CodeSymbol] = []
    if file_ids:
        stmt_syms = (
            select(CodeSymbol)
            .where(CodeSymbol.file_id.in_(file_ids))
            .order_by(CodeSymbol.start_line.asc())
        )
        symbols = list((await db.execute(stmt_syms)).scalars().all())

    # 3. Fetch Evidence items for architectural cross-referencing
    stmt_ev = select(Evidence).where(Evidence.project_id == project_id)
    evidence_items = list((await db.execute(stmt_ev)).scalars().all())

    # Group evidence by relative file path
    evidence_by_file: Dict[str, List[Evidence]] = {}
    for ev in evidence_items:
        evidence_by_file.setdefault(ev.file_path, []).append(ev)

    # 4. Parse blame for cataloged files
    file_blame_cache: Dict[str, Optional[Dict[int, LineBlameInfo]]] = {}
    if repo_dir and repo_dir.is_dir() and (repo_dir / ".git").exists():
        for file in analyzed_files:
            file_blame_cache[file.path] = await parse_file_blame(repo_dir, file.path)

    # 5. Process File-Level Ownership & Global Line Counts
    file_summaries: List[FileOwnershipSummary] = []
    global_author_counts: Dict[str, Tuple[str, int]] = {}
    total_repo_lines = 0
    candidate_repo_lines = 0

    file_by_id: Dict[uuid.UUID, AnalyzedFile] = {f.id: f for f in analyzed_files}

    for file in analyzed_files:
        lines_map = file_blame_cache.get(file.path)
        if lines_map:
            cand_pct, prim_auth, _, authors = compute_range_attribution(
                lines_map=lines_map,
                start_line=1,
                end_line=file.total_lines or len(lines_map),
                candidate_email=effective_email,
            )
            cand_lines = sum(
                a.lines_authored
                for a in authors
                if effective_email and (effective_email in a.email or a.email in effective_email)
            )
            for a in authors:
                if a.email not in global_author_counts:
                    global_author_counts[a.email] = (a.name, a.lines_authored)
                else:
                    g_name, g_count = global_author_counts[a.email]
                    global_author_counts[a.email] = (g_name, g_count + a.lines_authored)

            total_repo_lines += file.total_lines or len(lines_map)
            candidate_repo_lines += cand_lines

            file_summaries.append(
                FileOwnershipSummary(
                    file_path=file.path,
                    total_lines=file.total_lines or len(lines_map),
                    primary_author=prim_auth,
                    candidate_percentage=cand_pct,
                    candidate_lines=cand_lines,
                    authors=authors,
                )
            )
        else:
            # Fallback when repo is not on disk or uncommitted
            file_summaries.append(
                FileOwnershipSummary(
                    file_path=file.path,
                    total_lines=file.total_lines,
                    primary_author="Unknown",
                    candidate_percentage=0.0,
                    candidate_lines=0,
                    authors=[],
                )
            )

    # 6. Process Symbol-Level Ownership & Flag Unowned Load-Bearing Components
    symbol_ownership_list: List[SymbolOwnership] = []
    flagged_unowned: List[SymbolOwnership] = []
    candidate_authored_symbols_count = 0

    for sym in symbols:
        file = file_by_id.get(sym.file_id)
        if not file:
            continue

        lines_map = file_blame_cache.get(file.path)
        if lines_map:
            cand_pct, prim_auth, cand_status, authors = compute_range_attribution(
                lines_map=lines_map,
                start_line=sym.start_line,
                end_line=sym.end_line,
                candidate_email=effective_email,
            )
        else:
            cand_pct = 0.0
            prim_auth = "Unknown"
            cand_status = OwnershipStatus.UNOWNED
            authors = []

        if cand_status in (OwnershipStatus.PRIMARY, OwnershipStatus.COLLABORATOR):
            candidate_authored_symbols_count += 1

        # Check architectural evidence intersection
        is_ev = False
        ev_type: Optional[str] = None
        for ev in evidence_by_file.get(file.path, []):
            if ev.start_line <= sym.end_line and ev.end_line >= sym.start_line:
                is_ev = True
                ev_type = ev.evidence_type
                break

        sym_item = SymbolOwnership(
            symbol_id=str(sym.id),
            symbol_name=sym.name,
            symbol_type=sym.symbol_type,
            file_path=file.path,
            start_line=sym.start_line,
            end_line=sym.end_line,
            total_lines=max(0, sym.end_line - sym.start_line + 1),
            primary_author=prim_auth,
            candidate_ownership_percentage=cand_pct,
            candidate_status=cand_status,
            authors=authors,
            is_architectural_evidence=is_ev,
            evidence_type=ev_type,
        )
        symbol_ownership_list.append(sym_item)

        if is_ev and cand_status in (OwnershipStatus.UNOWNED, OwnershipStatus.MINOR):
            flagged_unowned.append(sym_item)

    # 7. Aggregate Top Contributors
    top_contributors: List[AuthorShare] = []
    if total_repo_lines > 0:
        sorted_global = sorted(global_author_counts.items(), key=lambda x: x[1][1], reverse=True)
        for email, (name, count) in sorted_global:
            pct = round((count / total_repo_lines) * 100.0, 1)
            top_contributors.append(
                AuthorShare(
                    name=name,
                    email=email,
                    lines_authored=count,
                    percentage=pct,
                )
            )

    overall_cand_pct = (
        round((candidate_repo_lines / total_repo_lines) * 100.0, 1)
        if total_repo_lines > 0
        else 0.0
    )

    return ProjectOwnershipReport(
        project_id=str(project_id),
        project_name=project.name,
        candidate_email=effective_email,
        total_symbols_analyzed=len(symbol_ownership_list),
        candidate_authored_symbols=candidate_authored_symbols_count,
        candidate_overall_ownership_percentage=overall_cand_pct,
        flagged_unowned_symbols=flagged_unowned,
        symbols=symbol_ownership_list,
        files=file_summaries,
        top_contributors=top_contributors,
    )
