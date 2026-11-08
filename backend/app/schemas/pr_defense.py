"""Pydantic v2 schemas for Pull Request defense sessions and diff-grounded questions."""

import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.defense import DefenseSessionState
from app.schemas.question import GroundedQuestion, QuestionCategory


class DiffGroundedQuestion(GroundedQuestion):
    """Evidence-grounded interview question anchored to a specific PR diff hunk.

    Extends the base GroundedQuestion with PR-specific citation fields so that
    every question maps back to a concrete file path and unified diff hunk header.
    """

    diff_file_path: str = Field(
        ...,
        description="Repository-relative path of the file changed in this PR",
    )
    diff_hunk_header: str = Field(
        ...,
        description="Unified diff hunk header identifying the changed region (@@ -old +new @@)",
    )
    change_type: str = Field(
        ...,
        description="Nature of the change: 'addition', 'deletion', or 'modification'",
    )
    cited_lines: List[str] = Field(
        default_factory=list,
        description="Actual diff lines ('+' additions or '-' deletions) quoted as evidence",
        max_length=60,
    )

    model_config = ConfigDict(extra="ignore")


class PRDefenseSessionState(DefenseSessionState):
    """Defense session state scoped exclusively to a Pull Request diff.

    Extends the base DefenseSessionState with PR metadata and replaces the
    generic question list with diff-grounded questions.
    """

    pr_number: int = Field(..., description="GitHub Pull Request number")
    pr_title: str = Field(..., description="Title of the Pull Request")
    pr_html_url: str = Field(..., description="GitHub web URL for the Pull Request")
    pr_author: str = Field(..., description="GitHub login of the PR author")
    pr_analysis_summary: str = Field(
        ...,
        description="Serialized narrative summary of the PR diff (files changed, +/- lines)",
    )
    diff_questions: List[DiffGroundedQuestion] = Field(
        default_factory=list,
        description="Ordered list of diff-grounded defense questions for this PR session",
    )

    model_config = ConfigDict(extra="ignore")


class StartPRDefenseRequest(BaseModel):
    """Payload to initiate a PR-scoped defense session."""

    pr_url: str = Field(
        ...,
        min_length=15,
        max_length=500,
        description=(
            "Public GitHub Pull Request URL "
            "(e.g. https://github.com/owner/repo/pull/123)"
        ),
    )
    num_questions: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of diff-grounded defense questions to generate (1-5)",
    )

    model_config = ConfigDict(extra="ignore")


def build_pr_grounded_question(
    diff_file_path: str,
    diff_hunk_header: str,
    change_type: str,
    cited_lines: List[str],
    question_text: str,
    context_hint: str,
    category: QuestionCategory = QuestionCategory.ARCHITECTURE,
) -> DiffGroundedQuestion:
    """Factory helper to construct a DiffGroundedQuestion with generated UUID."""
    return DiffGroundedQuestion(
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
    )
