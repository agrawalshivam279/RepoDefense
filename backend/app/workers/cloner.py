import asyncio
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select

from app.analyzers import persist_analyzed_files, scan_workspace_files
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
        raise ValueError(f"Dangerous branch name starts with dash: {branch}")
    if ".." in cleaned:
        raise ValueError(f"Dangerous branch name contains path traversal: {branch}")
    if not _SAFE_BRANCH_REGEX.match(cleaned):
        raise ValueError(f"Invalid characters in branch name: {branch}")
    return cleaned


async def run_git_shallow_clone(
    github_url: str,
    branch: str,
    target_dir: Path,
    timeout: float = 120.0,
) -> str:
    """Performs a shallow git clone of the target repository and returns HEAD commit hash.

    Args:
        github_url: Validated GitHub repository URL.
        branch: Target branch name.
        target_dir: Directory where the repository should be cloned.
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
        "--depth=1",
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
    rev_out, rev_err = await asyncio.wait_for(proc_rev.communicate(), timeout=15.0)
    if proc_rev.returncode != 0:
        err_msg = rev_err.decode(errors="replace").strip()
        logger.error("git_rev_parse_failed", returncode=proc_rev.returncode, stderr=err_msg)
        raise RuntimeError(f"git rev-parse HEAD failed: {err_msg}")

    commit_hash = rev_out.decode().strip()
    logger.info("git_clone_success", commit_hash=commit_hash)
    return commit_hash


async def clone_and_sanitize_repository(ctx: dict[str, Any], project_id: str) -> dict[str, Any]:
    """ARQ background worker job to clone, sanitize, and snapshot a GitHub repository.

    Args:
        ctx: ARQ worker context dictionary.
        project_id: UUID string of the project to process.

    Returns:
        Dictionary reporting execution status, commit hash, and file metrics.
    """
    project_uuid = uuid.UUID(project_id)

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
                summary_text = (
                    f"Cloned commit {commit_hash[:7]} with {len(files_meta)} files "
                    f"({total_lines} lines, {size_mb:.2f} MB). Languages: {top_langs_str}."
                )

                snapshot = RepositorySnapshot(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    commit_hash=commit_hash,
                    summary=summary_text,
                )
                session.add(snapshot)
                await persist_analyzed_files(session, snapshot.id, files_meta)

                project.status = "cloned"
                await session.commit()

            logger.info(
                "clone_and_sanitize_completed",
                project_id=project_id,
                commit_hash=commit_hash,
                valid_file_count=len(files_meta),
                total_lines=total_lines,
            )
            return {
                "status": "cloned",
                "commit_hash": commit_hash,
                "file_count": len(files_meta),
                "total_lines": total_lines,
                "total_bytes": sanitization.total_bytes,
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
