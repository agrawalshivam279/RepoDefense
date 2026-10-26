import asyncio
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select

from app.analyzers import (
    extract_and_persist_evidence,
    extract_and_persist_file_symbols,
    extract_git_history,
    persist_analyzed_files,
    scan_workspace_files,
)
from app.analyzers.dependencies import (
    extract_file_dependencies,
    get_dependency_parser,
    persist_dependencies,
)
from app.core.database import AsyncSessionLocal
from app.models.project import Project, RepositorySnapshot
from app.security.sanitizer import sanitize_workspace

logger = structlog.get_logger(__name__)

# Valid git branch name regex: alphanumeric, dots, underscores, slashes, dashes
_SAFE_BRANCH_REGEX = re.compile(r"^[a-zA-Z0-9_./-]+$")


def sanitize_git_branch(branch: str) -> str:
    """Validates and sanitizes a git branch name to prevent argument injection attacks.

    Raises:
        ValueError: If branch contains illegal characters, starts with a dash,
                    or contains path traversal dots.
    """
    cleaned = branch.strip()
    if not cleaned:
        raise ValueError("Branch name cannot be empty")
    if cleaned.startswith("-"):
        raise ValueError(f"Branch name cannot start with a dash: {branch}")
    if ".." in cleaned:
        raise ValueError(f"Path traversal characters not allowed in branch name: {branch}")
    if not _SAFE_BRANCH_REGEX.match(cleaned):
        raise ValueError(f"Invalid characters in branch name: {branch}")
    return cleaned


async def run_git_shallow_clone(
    github_url: str,
    branch: str,
    target_dir: Path,
    depth: int = 100,
    timeout: float = 120.0,
) -> str:
    """Performs a shallow git clone of the target repository and returns HEAD commit hash.

    Args:
        github_url: Validated GitHub repository URL.
        branch: Target branch name.
        target_dir: Directory where the repository should be cloned.
        depth: Commit history depth to fetch (defaults to 100 for history analysis).
        timeout: Subprocess execution timeout in seconds.

    Returns:
        40-character commit hash string.

    Raises:
        RuntimeError: If git command exits with non-zero status.
        asyncio.TimeoutError: If git clone exceeds timeout.
    """
    safe_branch = sanitize_git_branch(branch)
    clone_cmd = [
        "git",
        "clone",
        f"--depth={depth}",
        "--single-branch",
        "--branch",
        safe_branch,
        github_url,
        str(target_dir),
    ]

    logger.info("git_clone_started", url=github_url, branch=safe_branch, target=str(target_dir))
    proc = await asyncio.create_subprocess_exec(
        *clone_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip()
        logger.error("git_clone_failed", returncode=proc.returncode, stderr=err_msg)
        raise RuntimeError(f"git clone failed with code {proc.returncode}: {err_msg}")

    # Deterministically extract commit hash
    rev_cmd = ["git", "-C", str(target_dir), "rev-parse", "HEAD"]
    proc_rev = await asyncio.create_subprocess_exec(
        *rev_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_rev, stderr_rev = await asyncio.wait_for(proc_rev.communicate(), timeout=10.0)
    if proc_rev.returncode != 0:
        err_msg = stderr_rev.decode(errors="replace").strip()
        raise RuntimeError(f"git rev-parse HEAD failed: {err_msg}")

    commit_hash = stdout_rev.decode().strip()
    logger.info("git_clone_success", commit_hash=commit_hash, target=str(target_dir))
    return commit_hash


async def clone_and_sanitize_repository(ctx: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Background ARQ job that clones, sanitizes, and analyzes a GitHub repository.

    Flow:
        1. Look up project in DB and verify existence.
        2. Set project status to 'cloning'.
        3. Shallow clone repo into isolated tempdir using run_git_shallow_clone.
        4. Run sanitize_workspace to enforce quotas, strip secrets, and remove binary files.
        5. Scan workspace files and detect programming languages.
        6. Persist AnalyzedFile records to DB linked to a new RepositorySnapshot.
        7. Deterministically extract and persist CodeSymbol AST records via Tree-sitter.
        8. Extract and persist third-party dependencies and container/CI configs.
        9. Extract recent git commit history and aggregate contributor ownership.
        10. Update snapshot summary and set project status to 'cloned'.
    """
    project_uuid = uuid.UUID(project_id)
    logger.info("starting_clone_job", project_id=project_id)

    async with AsyncSessionLocal() as session:
        stmt = select(Project).where(Project.id == project_uuid)
        project = (await session.execute(stmt)).scalar_one_or_none()
        if not project:
            logger.error("project_not_found_for_cloning", project_id=project_id)
            return {"status": "failed", "error": f"Project {project_id} not found"}

        project.status = "cloning"
        await session.commit()
        github_url = project.github_url
        branch = project.default_branch

    with tempfile.TemporaryDirectory(prefix="repodefense_clone_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        try:
            commit_hash = await run_git_shallow_clone(github_url, branch, temp_dir)
            sanitization = sanitize_workspace(temp_dir)
            files_meta = scan_workspace_files(temp_dir, sanitization.valid_files)

            async with AsyncSessionLocal() as session:
                stmt = select(Project).where(Project.id == project_uuid)
                project = (await session.execute(stmt)).scalar_one()

                size_mb = sanitization.total_bytes / (1024 * 1024)
                lang_counts: dict[str, int] = {}
                total_lines = 0
                for f in files_meta:
                    lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
                    total_lines += f.total_lines

                top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                top_langs_str = ", ".join(f"{lang} ({cnt})" for lang, cnt in top_langs)

                snapshot = RepositorySnapshot(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    commit_hash=commit_hash,
                    summary="Processing snapshot files, symbols, dependencies, and git history...",
                )
                session.add(snapshot)
                created_files = await persist_analyzed_files(session, snapshot.id, files_meta)

                # 1. AST Symbol Extraction
                total_symbols = 0
                for af in created_files:
                    full_path = temp_dir / af.path
                    if full_path.is_file():
                        syms = await extract_and_persist_file_symbols(session, af, full_path)
                        total_symbols += len(syms)

                # 2. Dependency Manifest & Infrastructure Config Extraction
                total_deps = 0
                for af in created_files:
                    full_path = temp_dir / af.path
                    if full_path.is_file() and get_dependency_parser(af.path):
                        deps = extract_file_dependencies(af.path, full_path.read_bytes())
                        if deps:
                            await persist_dependencies(session, project.id, deps)
                            total_deps += len(deps)

                # 3. Git History & Contributor Extraction
                git_history = await extract_git_history(temp_dir, max_commits=100)
                contributors_str = ", ".join(
                    f"{c.name} ({c.percentage}%, {c.commit_count} commits)"
                    for c in git_history.contributors[:3]
                )

                # 4. Deterministic Architectural Evidence Extraction
                evidence_items = await extract_and_persist_evidence(
                    session, project.id, snapshot.id
                )
                total_evidence = len(evidence_items)

                summary_text = (
                    f"Cloned commit {commit_hash[:7]} with {len(files_meta)} files "
                    f"({total_lines} lines, {size_mb:.2f} MB, {total_symbols} symbols, "
                    f"{total_deps} dependencies, {total_evidence} evidence items). "
                    f"Languages: {top_langs_str}. "
                    f"Contributors ({git_history.total_commits} commits): "
                    f"{contributors_str or 'None'}."
                )
                snapshot.summary = summary_text
                project.status = "cloned"
                await session.commit()

            logger.info(
                "clone_and_sanitize_completed",
                project_id=project_id,
                commit_hash=commit_hash,
                valid_file_count=len(files_meta),
                total_lines=total_lines,
                symbol_count=total_symbols,
                dependency_count=total_deps,
                evidence_count=total_evidence,
                total_commits=git_history.total_commits,
                contributor_count=len(git_history.contributors),
                top_contributor=git_history.primary_author,
            )
            return {
                "status": "cloned",
                "commit_hash": commit_hash,
                "file_count": len(files_meta),
                "total_lines": total_lines,
                "total_bytes": sanitization.total_bytes,
                "symbol_count": total_symbols,
                "dependency_count": total_deps,
                "evidence_count": total_evidence,
                "total_commits": git_history.total_commits,
                "contributor_count": len(git_history.contributors),
                "top_contributor": git_history.primary_author,
            }

        except Exception as exc:
            logger.error(
                "clone_and_sanitize_failed",
                project_id=project_id,
                error=str(exc),
            )
            async with AsyncSessionLocal() as session:
                stmt = select(Project).where(Project.id == project_uuid)
                project = (await session.execute(stmt)).scalar_one_or_none()
                if project:
                    project.status = "failed"
                    await session.commit()

            return {
                "status": "failed",
                "error": str(exc),
            }
