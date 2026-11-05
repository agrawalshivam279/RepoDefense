"""Deterministic Git blame porcelain parser for code symbol and line ownership attribution."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

from app.schemas.ownership import AuthorShare, OwnershipStatus

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LineBlameInfo:
    """Line-level authorship attribution extracted from git blame --line-porcelain."""

    line_number: int
    author_name: str
    author_email: str
    commit_hash: str


async def parse_file_blame(
    repo_dir: Path,
    rel_file_path: str,
    timeout: float = 15.0,
) -> Optional[Dict[int, LineBlameInfo]]:
    """Runs git blame on a repository file using --line-porcelain and parses line authorship.

    Executes git via asyncio.create_subprocess_exec with an explicit argument array.
    Never executes arbitrary repository code or invokes a shell.

    Args:
        repo_dir: Local directory path containing the cloned repository (.git root).
        rel_file_path: Relative file path from the repository root.
        timeout: Subprocess execution timeout in seconds.

    Returns:
        Dictionary mapping 1-indexed line numbers to LineBlameInfo, or None on failure.
    """
    if not repo_dir.is_dir() or not (repo_dir / ".git").exists():
        logger.warning("git_blame_skipped_not_a_repo", path=str(repo_dir))
        return None

    full_path = (repo_dir / rel_file_path).resolve()
    repo_resolved = repo_dir.resolve()

    # Prevent path traversal attacks
    if not full_path.is_relative_to(repo_resolved):
        logger.warning(
            "git_blame_path_traversal_blocked",
            rel_path=rel_file_path,
            repo_dir=str(repo_dir),
        )
        return None

    if not full_path.is_file():
        return None

    cmd = [
        "git",
        "-C",
        str(repo_dir),
        "blame",
        "--line-porcelain",
        "--",
        rel_file_path,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("git_blame_timeout", file=rel_file_path, timeout=timeout)
        return None
    except Exception as exc:
        logger.warning("git_blame_exec_failed", file=rel_file_path, error=str(exc))
        return None

    if proc.returncode != 0:
        logger.debug(
            "git_blame_nonzero_exit",
            file=rel_file_path,
            code=proc.returncode,
            stderr=stderr.decode(errors="replace").strip(),
        )
        return None

    output = stdout.decode("utf-8", errors="replace")
    return parse_line_porcelain_output(output)


def parse_line_porcelain_output(output: str) -> Dict[int, LineBlameInfo]:
    """Parses raw stdout from git blame --line-porcelain into LineBlameInfo records.

    Format structure:
    <40-char-sha> <orig_line> <final_line> [<group_lines>]
    author <name>
    author-mail <<email>>
    ...
    \\t<source_line>
    """
    lines_map: Dict[int, LineBlameInfo] = {}

    current_sha = ""
    current_line_no = 0
    current_author_name = "Unknown"
    current_author_email = "unknown@example.com"

    for line in output.splitlines():
        if not line:
            continue

        if line.startswith("\t"):
            # End of block for this line
            if current_line_no > 0:
                lines_map[current_line_no] = LineBlameInfo(
                    line_number=current_line_no,
                    author_name=current_author_name,
                    author_email=current_author_email,
                    commit_hash=current_sha,
                )
            continue

        parts = line.split(" ", 1)
        token = parts[0]

        if len(token) == 40 and all(c in "0123456789abcdefABCDEF" for c in token):
            # Header line: <sha> <orig_line> <final_line>
            subparts = line.split()
            current_sha = subparts[0]
            if len(subparts) >= 3 and subparts[2].isdigit():
                current_line_no = int(subparts[2])
            elif len(subparts) >= 2 and subparts[1].isdigit():
                current_line_no = int(subparts[1])
        elif token == "author" and len(parts) > 1:
            current_author_name = parts[1].strip()
        elif token == "author-mail" and len(parts) > 1:
            raw_mail = parts[1].strip()
            current_author_email = raw_mail.strip("<>").lower()

    return lines_map


def compute_range_attribution(
    lines_map: Dict[int, LineBlameInfo],
    start_line: int,
    end_line: int,
    candidate_email: str,
) -> Tuple[float, str, OwnershipStatus, List[AuthorShare]]:
    """Calculates author shares and candidate ownership status for a specified line range.

    Args:
        lines_map: 1-indexed dictionary of LineBlameInfo.
        start_line: Inclusive 1-indexed start line.
        end_line: Inclusive 1-indexed end line.
        candidate_email: Normalized email of the candidate.

    Returns:
        Tuple of (candidate_percentage, primary_author, candidate_status, authors_list).
    """
    start = max(1, start_line)
    end = max(start, end_line)

    author_counts: Dict[str, Tuple[str, int]] = {}
    candidate_lines = 0
    total_found = 0
    norm_candidate = candidate_email.strip().lower()

    for line_no in range(start, end + 1):
        info = lines_map.get(line_no)
        if not info:
            continue

        total_found += 1
        email_key = info.author_email.lower()
        if email_key not in author_counts:
            author_counts[email_key] = (info.author_name, 1)
        else:
            name, count = author_counts[email_key]
            author_counts[email_key] = (name, count + 1)

        if norm_candidate and (
            norm_candidate == email_key
            or norm_candidate in email_key
            or email_key in norm_candidate
        ):
            candidate_lines += 1

    if total_found == 0:
        return 0.0, "Unknown", OwnershipStatus.UNOWNED, []

    # Sort authors by lines authored descending
    sorted_authors = sorted(author_counts.items(), key=lambda x: x[1][1], reverse=True)
    primary_author = sorted_authors[0][1][0] if sorted_authors else "Unknown"

    authors_list: List[AuthorShare] = []
    for email, (name, count) in sorted_authors:
        pct = round((count / total_found) * 100.0, 1)
        authors_list.append(
            AuthorShare(
                name=name,
                email=email,
                lines_authored=count,
                percentage=pct,
            )
        )

    cand_pct = round((candidate_lines / total_found) * 100.0, 1)

    if cand_pct >= 80.0:
        status = OwnershipStatus.PRIMARY
    elif cand_pct >= 20.0:
        status = OwnershipStatus.COLLABORATOR
    elif cand_pct > 0.0:
        status = OwnershipStatus.MINOR
    else:
        status = OwnershipStatus.UNOWNED

    return cand_pct, primary_author, status, authors_list
