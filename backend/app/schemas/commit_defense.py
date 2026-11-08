"""Pydantic v2 schemas for Git Commit defense sessions and diff-grounded questions."""

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.defense import DefenseSessionState
from app.schemas.pr_analysis import ParsedFileDiff
from app.schemas.pr_defense import DiffGroundedQuestion
from app.schemas.question import QuestionCategory


class CommitMetadata(BaseModel):
    """Structured metadata for a specific Git commit fetched via GitHub API."""

    commit_hash: str = Field(..., description="Commit SHA (7 to 40 hex chars)")
    author_name: str = Field(..., description="Commit author display name")
    author_email: Optional[str] = Field(default=None, description="Commit author email")
    committed_at: str = Field(..., description="ISO 8601 commit timestamp")
    message: str = Field(..., description="Commit message subject/summary")
    html_url: str = Field(..., description="Web URL for the commit on GitHub")
    total_additions: int = Field(default=0, ge=0, description="Total added lines")
    total_deletions: int = Field(default=0, ge=0, description="Total deleted lines")
    total_files: int = Field(default=0, ge=0, description="Count of changed files")

    model_config = ConfigDict(extra="ignore")


class CommitAnalysisResponse(BaseModel):
    """Structured inspection payload for a Git commit and its parsed diff hunks."""

    metadata: CommitMetadata = Field(..., description="Commit author and metadata")
    files: List[ParsedFileDiff] = Field(default_factory=list, description="Parsed diffs per file")
    total_files_changed: int = Field(..., ge=0, description="Number of changed files")
    total_additions: int = Field(..., ge=0, description="Total additions across all files")
    total_deletions: int = Field(..., ge=0, description="Total deletions across all files")
    summary_narrative: str = Field(..., description="Concise textual summary of changes")

    model_config = ConfigDict(extra="ignore")


class CommitGroundedQuestion(DiffGroundedQuestion):
    """Evidence-grounded question anchored to a specific commit diff hunk."""

    commit_hash: str = Field(..., description="Commit SHA anchoring this question")

    model_config = ConfigDict(extra="ignore")


class CommitDefenseSessionState(DefenseSessionState):
    """Defense session state scoped exclusively to changes in a single commit."""

    commit_hash: str = Field(..., description="Git commit hash (SHA)")
    commit_message: str = Field(..., description="Commit message subject")
    commit_author: str = Field(..., description="Author of the commit")
    commit_html_url: str = Field(..., description="GitHub URL for this commit")
    commit_analysis_summary: str = Field(
        ..., description="Serialized narrative summary of commit changes"
    )
    diff_questions: List[CommitGroundedQuestion] = Field(
        default_factory=list,
        description="Ordered list of diff-grounded questions for this commit",
    )

    model_config = ConfigDict(extra="ignore")


class StartCommitDefenseRequest(BaseModel):
    """Payload to initiate a commit-scoped defense session."""

    commit_url_or_hash: str = Field(
        ...,
        min_length=7,
        max_length=500,
        description=(
            "GitHub commit URL (e.g. https://github.com/owner/repo/commit/sha) "
            "or a 7-40 char commit SHA"
        ),
    )
    num_questions: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of diff-grounded defense questions to generate (1-5)",
    )

    model_config = ConfigDict(extra="ignore")


def build_commit_grounded_question(
    diff_file_path: str,
    diff_hunk_header: str,
    change_type: str,
    cited_lines: List[str],
    question_text: str,
    context_hint: str,
    commit_hash: str,
    category: QuestionCategory = QuestionCategory.ARCHITECTURE,
) -> CommitGroundedQuestion:
    """Factory helper to construct a CommitGroundedQuestion with a generated UUID."""
    return CommitGroundedQuestion(
        id=str(uuid.uuid4()),
        category=category,
        question_text=question_text,
        context_hint=context_hint,
        cited_evidence_ids=[],
        cited_files=[diff_file_path],
        diff_file_path=diff_file_path,
        diff_hunk_header=diff_hunk_header,
        change_type=change_type,
        cited_lines=cited_lines[:60],
        commit_hash=commit_hash,
    )
