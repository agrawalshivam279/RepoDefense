"""GitHub Git Commit metadata fetcher, diff retriever, and session builder."""

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
import structlog
from fastapi import HTTPException, status

from app.ai.fsm import DefenseSessionStore
from app.ai.pr_question_generator import generate_pr_defense_questions
from app.analyzers.diff_parser import DiffParsingError, parse_unified_diff
from app.schemas.commit_defense import (
    CommitDefenseSessionState,
    CommitGroundedQuestion,
    CommitMetadata,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseStage,
    DefenseTurn,
    DifficultyLevel,
    TurnRole,
)
from app.schemas.pr_analysis import PRAnalysisResponse, PRMetadata

logger = structlog.get_logger(__name__)

COMMIT_URL_REGEX = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/commit/([a-fA-F0-9]{7,40})(?:/.*)?$"
)
COMMIT_SHA_REGEX = re.compile(r"^[a-fA-F0-9]{7,40}$")
PROJECT_REPO_REGEX = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?(?:/.*)?$"
)


def parse_github_commit_url_or_sha(
    input_val: str, project_github_url: Optional[str] = None
) -> Tuple[str, str, str]:
    """Extracts (owner, repo, commit_sha) from a commit URL or raw hex SHA."""
    val = input_val.strip()
    match = COMMIT_URL_REGEX.match(val)
    if match:
        return match.group(1), match.group(2), match.group(3)

    if COMMIT_SHA_REGEX.match(val) and project_github_url:
        proj_match = PROJECT_REPO_REGEX.match(project_github_url.strip())
        if proj_match:
            return proj_match.group(1), proj_match.group(2), val

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid commit reference. Provide a GitHub commit URL or a 7-40 char hex SHA.",
    )


async def fetch_github_commit_data(
    owner: str, repo: str, sha: str, client: Optional[httpx.AsyncClient] = None
) -> Tuple[CommitMetadata, str]:
    """Fetches commit metadata JSON and unified diff patch text from GitHub REST API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    http = client if client is not None else httpx.AsyncClient(timeout=15.0)

    try:
        res = await http.get(api_url, headers={"User-Agent": "RepoDefense-CommitParser/1.0"})
        if res.status_code == 404:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Commit '{sha}' was not found in repository {owner}/{repo}.",
            )
        if res.status_code in (403, 429):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "GitHub API rate limit exceeded. Please try again later.",
            )
        if res.status_code != 200:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"GitHub API error fetching commit metadata: {res.status_code}",
            )
        data = res.json()

        diff_res = await http.get(
            api_url,
            headers={
                "User-Agent": "RepoDefense-CommitParser/1.0",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        if diff_res.status_code != 200:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"GitHub API error fetching commit diff: {diff_res.status_code}",
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Network error connecting to GitHub: {exc}",
        ) from exc
    finally:
        if client is None:
            await http.aclose()

    author_obj = data.get("commit", {}).get("author", {}) or {}
    stats_obj = data.get("stats", {}) or {}
    files_list = data.get("files", []) or []

    meta = CommitMetadata(
        commit_hash=data.get("sha", sha),
        author_name=author_obj.get("name", "Unknown"),
        author_email=author_obj.get("email"),
        committed_at=author_obj.get("date", datetime.now(timezone.utc).isoformat()),
        message=data.get("commit", {}).get("message", "").split("\n")[0] or "No commit message",
        html_url=data.get("html_url", f"https://github.com/{owner}/{repo}/commit/{sha}"),
        total_additions=stats_obj.get("additions", 0),
        total_deletions=stats_obj.get("deletions", 0),
        total_files=len(files_list),
    )
    return meta, diff_res.text


async def build_commit_session(
    project_id: str,
    meta: CommitMetadata,
    diff_text: str,
    num_questions: int,
    store: DefenseSessionStore,
) -> CommitDefenseSessionState:
    """Parses diff, generates commit-grounded questions, and initializes session state."""
    try:
        parsed_files = parse_unified_diff(diff_text)
    except DiffParsingError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Failed to parse commit diff: {exc}"
        ) from exc

    if not parsed_files:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Commit '{meta.commit_hash[:7]}' has no changes to defend.",
        )

    adds = sum(f.total_additions for f in parsed_files)
    dels = sum(f.total_deletions for f in parsed_files)
    narrative = f"Commit {meta.commit_hash[:7]} ('{meta.message}') (+{adds}, -{dels})."

    pr_compat = PRAnalysisResponse(
        metadata=PRMetadata(
            pr_number=0,
            title=meta.message,
            author=meta.author_name,
            base_branch="main",
            head_branch=meta.commit_hash[:7],
            head_sha=meta.commit_hash,
            html_url=meta.html_url,
            created_at=meta.committed_at,
        ),
        files=parsed_files,
        total_files_changed=len(parsed_files),
        total_additions=adds,
        total_deletions=dels,
        summary_narrative=narrative,
    )

    diff_qs = await generate_pr_defense_questions(pr_compat, num_questions)
    commit_qs = [
        CommitGroundedQuestion(
            **q.model_dump(exclude={"commit_hash"}),
            commit_hash=meta.commit_hash,
        )
        for q in diff_qs
    ]

    q_progress = [
        DefenseQuestionProgress(
            question=q,
            status=DefenseStage.QUESTION_ACTIVE if i == 0 else DefenseStage.INITIALIZING,
            difficulty=DifficultyLevel.INTERMEDIATE,
        )
        for i, q in enumerate(commit_qs)
    ]
    first_q, now_iso = commit_qs[0], datetime.now(timezone.utc).isoformat()
    turn_content = (
        f"Question 1/{len(commit_qs)} [COMMIT DEFENSE]:\n\n{first_q.question_text}\n\n"
        f"Context: `{first_q.diff_file_path}` at `{first_q.diff_hunk_header}`"
    )

    session = CommitDefenseSessionState(
        project_id=project_id,
        status=DefenseStage.QUESTION_ACTIVE,
        current_question_index=0,
        current_difficulty=DifficultyLevel.INTERMEDIATE,
        total_questions=len(commit_qs),
        questions=q_progress,
        created_at=now_iso,
        updated_at=now_iso,
        commit_hash=meta.commit_hash,
        commit_message=meta.message,
        commit_author=meta.author_name,
        commit_html_url=meta.html_url,
        commit_analysis_summary=narrative,
        diff_questions=commit_qs,
        turns=[
            DefenseTurn(
                role=TurnRole.INTERVIEWER,
                content=turn_content,
                stage=DefenseStage.QUESTION_ACTIVE,
                metadata={"question_id": first_q.id, "diff_file_path": first_q.diff_file_path},
            )
        ],
    )
    await store.save(session)
    logger.info(
        "commit_defense_session_created", session_id=session.session_id, sha=meta.commit_hash
    )
    return session
