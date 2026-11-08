"""FastAPI REST router for GitHub Pull Request diff ingestion, parsing, and analysis."""

import re
import uuid
from typing import Optional, Tuple

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.diff_parser import DiffParsingError, parse_unified_diff
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.pr_analysis import (
    ParsedFileDiff,
    PRAnalysisRequest,
    PRAnalysisResponse,
    PRMetadata,
    RawDiffParseRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/pr", tags=["pull-requests"])

PR_URL_REGEX = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(\d+)(?:/.*)?$"
)


def parse_github_pr_url(url: str) -> Tuple[str, str, int]:
    """Validates and extracts owner, repo name, and PR number from a GitHub PR URL."""
    match = PR_URL_REGEX.match(url.strip())
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid GitHub Pull Request URL. Expected format: "
                "https://github.com/{owner}/{repo}/pull/{number}"
            ),
        )
    return match.group(1), match.group(2), int(match.group(3))


async def fetch_github_pr_data(
    owner: str,
    repo: str,
    pr_number: int,
    client: Optional[httpx.AsyncClient] = None,
) -> Tuple[PRMetadata, str]:
    """Fetches PR metadata JSON and unified diff patch text from the GitHub REST API."""
    api_base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers_common = {
        "User-Agent": "RepoDefense-DiffParser/1.0",
    }

    own_client = client is None
    http = client if client is not None else httpx.AsyncClient(timeout=15.0)

    try:
        # 1. Fetch PR Metadata
        meta_resp = await http.get(api_base, headers=headers_common)
        if meta_resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pull request #{pr_number} was not found in repository {owner}/{repo}.",
            )
        if meta_resp.status_code in (403, 429):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later.",
            )
        if meta_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching metadata: {meta_resp.status_code}",
            )

        meta_data = meta_resp.json()
        pr_meta = PRMetadata(
            pr_number=pr_number,
            title=meta_data.get("title", f"PR #{pr_number}"),
            body=meta_data.get("body"),
            author=meta_data.get("user", {}).get("login", "unknown"),
            base_branch=meta_data.get("base", {}).get("ref", "main"),
            head_branch=meta_data.get("head", {}).get("ref", "unknown"),
            head_sha=meta_data.get("head", {}).get("sha", ""),
            state=meta_data.get("state", "open"),
            html_url=meta_data.get("html_url", api_base),
            created_at=meta_data.get("created_at", ""),
        )

        # 2. Fetch Unified Diff
        diff_headers = {**headers_common, "Accept": "application/vnd.github.v3.diff"}
        diff_resp = await http.get(api_base, headers=diff_headers)
        if diff_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching PR diff: {diff_resp.status_code}",
            )

        return pr_meta, diff_resp.text

    finally:
        if own_client:
            await http.aclose()


@router.post(
    "/parse-diff",
    response_model=list[ParsedFileDiff],
    summary="Parse raw unified diff text",
)
async def parse_raw_diff_endpoint(
    payload: RawDiffParseRequest,
) -> list[ParsedFileDiff]:
    """Parses a raw unified git diff stream into structured file diffs and hunks."""
    try:
        return parse_unified_diff(payload.diff_text)
    except DiffParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/projects/{project_id}/analyze",
    response_model=PRAnalysisResponse,
    summary="Ingest and analyze a GitHub Pull Request for a project",
)
async def analyze_project_pr_endpoint(
    project_id: uuid.UUID,
    payload: PRAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PRAnalysisResponse:
    """Fetches a PR diff via GitHub API, parses hunks, and maps changes to the target project."""
    # 1. Enforce multi-tenant project ownership
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # 2. Parse GitHub PR URL and fetch diff
    owner, repo, pr_number = parse_github_pr_url(payload.pr_url)
    try:
        pr_meta, diff_text = await fetch_github_pr_data(owner, repo, pr_number)
        parsed_files = parse_unified_diff(diff_text)
    except DiffParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse PR diff: {exc}",
        ) from exc

    total_adds = sum(f.total_additions for f in parsed_files)
    total_dels = sum(f.total_deletions for f in parsed_files)
    narrative = (
        f"Pull Request #{pr_meta.pr_number} ('{pr_meta.title}') authored by @{pr_meta.author} "
        f"modifies {len(parsed_files)} file(s) (+{total_adds}, -{total_dels}) across branch "
        f"'{pr_meta.head_branch}' into '{pr_meta.base_branch}'."
    )

    logger.info(
        "pr_analysis_completed",
        project_id=str(project_id),
        pr_number=pr_meta.pr_number,
        files_count=len(parsed_files),
        additions=total_adds,
        deletions=total_dels,
    )

    return PRAnalysisResponse(
        metadata=pr_meta,
        files=parsed_files,
        total_files_changed=len(parsed_files),
        total_additions=total_adds,
        total_deletions=total_dels,
        summary_narrative=narrative,
    )
