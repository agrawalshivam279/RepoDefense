import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Unit Separator character used to deterministically split git log fields
DELIMITER = "\x1f"


class GitCommitMetadata(BaseModel):
    """Structured representation of a single git commit extracted via git log."""

    commit_hash: str = Field(..., description="40-character hex commit SHA")
    author_name: str = Field(..., description="Commit author display name")
    author_email: str = Field(..., description="Commit author email address")
    committed_at: datetime = Field(..., description="ISO 8601 commit timestamp with timezone")
    message: str = Field(..., description="Commit subject line")
    files_changed: list[str] = Field(
        default_factory=list,
        description="Repository-relative file paths touched in commit",
    )


class ContributorStats(BaseModel):
    """Aggregated activity and velocity statistics for a single repository contributor."""

    name: str = Field(..., description="Contributor name (most recent observed)")
    email: str = Field(..., description="Normalized lowercase email address")
    commit_count: int = Field(..., description="Number of commits authored in sample")
    percentage: float = Field(..., description="Percentage of total sampled commits (0.0 to 100.0)")
    files_touched_count: int = Field(
        ...,
        description="Count of distinct files modified by contributor",
    )
    first_commit_at: Optional[datetime] = Field(
        None,
        description="Timestamp of earliest commit in sample",
    )
    last_commit_at: Optional[datetime] = Field(
        None,
        description="Timestamp of most recent commit in sample",
    )


class GitHistorySummary(BaseModel):
    """Complete summary of recent repository commit history and contributor ownership."""

    total_commits: int = Field(0, description="Total number of commits parsed (up to max_commits)")
    commits: list[GitCommitMetadata] = Field(
        default_factory=list,
        description="Chronological list of parsed commits (most recent first)",
    )
    contributors: list[ContributorStats] = Field(
        default_factory=list,
        description="Contributors sorted by commit count descending",
    )
    primary_author: Optional[str] = Field(
        None,
        description="Name of the top contributor by commit count",
    )


async def extract_git_history(
    repo_dir: Path,
    max_commits: int = 100,
    timeout: float = 30.0,
) -> GitHistorySummary:
    """Extracts recent commit history and contributor activity metrics from a git repository.

    Uses `asyncio.create_subprocess_exec` to run `git log` with deterministic unit separator
    delimiters. Never executes arbitrary user code or git hooks. If the directory is not a
    valid git repository or git log fails, returns an empty GitHistorySummary safely.

    Args:
        repo_dir: Local filesystem path to the root of the cloned repository.
        max_commits: Maximum number of recent commits to analyze (default 100).
        timeout: Subprocess execution timeout in seconds.

    Returns:
        GitHistorySummary containing parsed commits and aggregated contributor metrics.
    """
    if not repo_dir.is_dir() or not (repo_dir / ".git").exists():
        logger.warning("git_history_skipped_not_a_repo", path=str(repo_dir))
        return GitHistorySummary()

    # --pretty format uses %x1f (Unit Separator): hash, name, email, ISO date, subject
    cmd = [
        "git",
        "-C",
        str(repo_dir),
        "log",
        f"-n{max_commits}",
        "--no-color",
        f"--pretty=format:%H{DELIMITER}%an{DELIMITER}%ae{DELIMITER}%aI{DELIMITER}%s",
        "--name-only",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("git_log_timed_out", path=str(repo_dir), timeout=timeout)
        return GitHistorySummary()
    except Exception as exc:
        logger.error("git_log_subprocess_error", path=str(repo_dir), error=str(exc))
        return GitHistorySummary()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip()
        logger.warning("git_log_command_failed", returncode=proc.returncode, stderr=err_msg)
        return GitHistorySummary()

    raw_output = stdout.decode(errors="replace")
    if not raw_output.strip():
        return GitHistorySummary()

    return _parse_git_log_output(raw_output)


def _parse_git_log_output(output: str) -> GitHistorySummary:
    """Parses raw delimited git log output into structured commit and contributor models."""
    commits: list[GitCommitMetadata] = []
    current_commit: Optional[dict] = None
    lines = output.splitlines()

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        if DELIMITER in line:
            # Finalize previous commit if present
            if current_commit:
                commits.append(GitCommitMetadata(**current_commit))

            tokens = line.split(DELIMITER)
            if len(tokens) >= 5:
                commit_hash = tokens[0].strip()
                author_name = tokens[1].strip()
                author_email = tokens[2].strip()
                date_str = tokens[3].strip()
                subject = DELIMITER.join(tokens[4:]).strip()

                try:
                    committed_at = datetime.fromisoformat(date_str)
                except ValueError:
                    # Fallback in case of non-standard ISO date format
                    committed_at = datetime.now()

                current_commit = {
                    "commit_hash": commit_hash,
                    "author_name": author_name,
                    "author_email": author_email,
                    "committed_at": committed_at,
                    "message": subject,
                    "files_changed": [],
                }
            else:
                current_commit = None
        elif current_commit is not None:
            # File modified by current commit
            current_commit["files_changed"].append(line_str)

    if current_commit:
        commits.append(GitCommitMetadata(**current_commit))

    total_commits = len(commits)
    if total_commits == 0:
        return GitHistorySummary()

    contributors = _calculate_contributor_stats(commits)
    primary_author = contributors[0].name if contributors else None

    return GitHistorySummary(
        total_commits=total_commits,
        commits=commits,
        contributors=contributors,
        primary_author=primary_author,
    )


def _calculate_contributor_stats(commits: list[GitCommitMetadata]) -> list[ContributorStats]:
    """Aggregates commit frequency, file coverage, and velocity per unique author email."""
    # Key: normalized email -> aggregate state
    author_map: dict[str, dict] = {}
    total_commits = len(commits)

    for c in commits:
        email_key = c.author_email.strip().lower()
        if not email_key:
            email_key = c.author_name.strip().lower()

        if email_key not in author_map:
            author_map[email_key] = {
                "name": c.author_name,
                "email": c.author_email,
                "count": 0,
                "files": set(),
                "first_date": c.committed_at,
                "last_date": c.committed_at,
            }

        data = author_map[email_key]
        data["count"] += 1
        data["files"].update(c.files_changed)
        # Always keep most recent author display name
        data["name"] = c.author_name

        if c.committed_at < data["first_date"]:
            data["first_date"] = c.committed_at
        if c.committed_at > data["last_date"]:
            data["last_date"] = c.committed_at

    contributors: list[ContributorStats] = []
    for data in author_map.values():
        percentage = round((data["count"] / total_commits) * 100.0, 1) if total_commits > 0 else 0.0
        contributors.append(
            ContributorStats(
                name=data["name"],
                email=data["email"],
                commit_count=data["count"],
                percentage=percentage,
                files_touched_count=len(data["files"]),
                first_commit_at=data["first_date"],
                last_commit_at=data["last_date"],
            )
        )

    # Sort descending by commit count, breaking ties by name
    contributors.sort(key=lambda x: (-x.commit_count, x.name.lower()))
    return contributors
