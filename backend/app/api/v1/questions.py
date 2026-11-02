"""FastAPI router for generating and retrieving evidence-grounded interview questions."""

import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import generate_grounded_questions
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.analysis import Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.question import (
    EvidenceRef,
    QuestionGenerationInput,
    QuestionGenerationResponse,
)

router = APIRouter(prefix="/projects", tags=["Questions"])


@router.post(
    "/{project_id}/questions",
    response_model=QuestionGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate evidence-grounded interview questions for a project",
    description=(
        "Retrieves project metadata, latest snapshot narrative, and extracted evidence items, "
        "and synthesizes challenging technical questions citing specific codebase components."
    ),
)
async def generate_project_questions(
    project_id: uuid.UUID,
    count: int = Query(default=3, ge=1, le=10, description="Number of questions to synthesize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionGenerationResponse:
    """Generates structured, categorized questions for the specified project."""
    # 1. Tenancy check
    stmt_proj = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt_proj)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Fetch latest snapshot for summary narrative
    stmt_snap = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = (await db.execute(stmt_snap)).scalar_one_or_none()

    narrative: Optional[str] = None
    style: Optional[str] = None
    if snapshot and snapshot.summary:
        try:
            summary_data = json.loads(snapshot.summary)
            if isinstance(summary_data, dict):
                narrative = summary_data.get("narrative")
                style = summary_data.get("architectural_style")
        except Exception:
            narrative = snapshot.summary

    # 3. Fetch evidence records
    stmt_ev = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .order_by(Evidence.id)
    )
    evidence_rows = (await db.execute(stmt_ev)).scalars().all()

    evidence_refs: List[EvidenceRef] = [
        EvidenceRef(
            id=str(ev.id),
            evidence_type=ev.evidence_type,
            title=ev.title,
            description=ev.description,
            file_path=ev.file_path,
            start_line=ev.start_line,
            end_line=ev.end_line,
        )
        for ev in evidence_rows
    ]

    # 4. Formulate generation input
    gen_input = QuestionGenerationInput(
        project_name=project.name,
        summary_narrative=narrative,
        architectural_style=style,
        evidence_items=evidence_refs,
        requested_count=count,
    )

    # 5. Synthesize questions via LiteLLM
    questions = await generate_grounded_questions(gen_input)

    # 6. Compute grounded metrics
    all_cited_ids = {ev_id for q in questions for ev_id in q.cited_evidence_ids if ev_id}

    return QuestionGenerationResponse(
        project_id=project.id,
        project_name=project.name,
        questions=questions,
        total_generated=len(questions),
        grounded_evidence_count=len(all_cited_ids),
    )
