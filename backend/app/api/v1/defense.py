"""FastAPI router for managing interactive defense sessions and the interview core loop."""

import json
import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import create_defense_session, defense_store, submit_defense_turn
from app.ai.llm import generate_grounded_questions
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.analysis import Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.defense import (
    DefenseSessionState,
    StartDefenseRequest,
    SubmitAnswerRequest,
)
from app.schemas.question import EvidenceRef, QuestionGenerationInput

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Defense"])


@router.post(
    "/projects/{project_id}/defense/start",
    response_model=DefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Start an evidence-grounded defense session for a repository",
    description=(
        "Retrieves repository evidence, generates targeted technical questions, "
        "and initializes the interview state machine (FSM)."
    ),
)
async def start_defense_session(
    project_id: uuid.UUID,
    payload: Optional[StartDefenseRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DefenseSessionState:
    """Initiates an architectural defense session against repository evidence."""
    request_data = payload or StartDefenseRequest()

    # 1. Tenancy verification
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

    # 2. Retrieve snapshot narrative
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
            summary_dict = json.loads(snapshot.summary)
            if isinstance(summary_dict, dict):
                narrative = summary_dict.get("narrative")
                style = summary_dict.get("architectural_style")
        except Exception:
            narrative = snapshot.summary

    # 3. Retrieve evidence items
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

    # 4. Generate grounded questions
    gen_input = QuestionGenerationInput(
        project_name=project.name,
        summary_narrative=narrative,
        architectural_style=style,
        evidence_items=evidence_refs,
        requested_count=request_data.num_questions,
    )
    questions = await generate_grounded_questions(gen_input)

    # Filter by custom categories if specified
    if request_data.custom_categories:
        cats = {c.lower() for c in request_data.custom_categories}
        filtered = [q for q in questions if q.category.value.lower() in cats]
        if filtered:
            questions = filtered

    selected_questions = questions[: request_data.num_questions]
    if not selected_questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to formulate grounded defense questions for this project.",
        )

    # 5. Initialize FSM session
    session = await create_defense_session(
        project_id=str(project.id),
        questions=selected_questions,
    )
    return session


@router.post(
    "/defense/sessions/{session_id}/answer",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate answer or defense turn",
    description=(
        "Submits candidate defense to the FSM. Depending on current stage, "
        "evaluates depth, triggers stress test, provides mentor guidance, or advances question."
    ),
)
async def submit_defense_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> DefenseSessionState:
    """Processes candidate defense turn through the deterministic interview FSM."""
    try:
        session = await submit_defense_turn(
            session_id=session_id,
            candidate_answer=payload.answer,
        )
        return session
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defense session '{session_id}' not found.",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )


@router.get(
    "/defense/sessions/{session_id}",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current state and transcript of a defense session",
)
async def get_defense_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> DefenseSessionState:
    """Retrieves current interview state, transcript, and scores for a session."""
    session = await defense_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defense session '{session_id}' not found.",
        )
    return session
