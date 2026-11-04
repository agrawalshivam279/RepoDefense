"""FastAPI router for managing interactive defense sessions and the interview core loop."""

import json
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fsm import create_defense_session, defense_store, submit_defense_turn
from app.ai.llm import generate_grounded_questions
from app.ai.report_generator import generate_defense_report
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.analysis import Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.defense import (
    DefenseSessionState,
    DefenseStage,
    StartDefenseRequest,
    SubmitAnswerRequest,
)
from app.schemas.question import EvidenceRef, QuestionGenerationInput
from app.schemas.report import DefenseReportResponse

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
    """Initiates an architectural defense session grounded in repository evidence."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    snap_stmt = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
    )
    snapshot = (await db.execute(snap_stmt)).scalars().first()

    ev_stmt = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .order_by(Evidence.start_line)
    )
    evidence_rows = (await db.execute(ev_stmt)).scalars().all()

    evidence_items = [
        EvidenceRef(
            id=str(row.id),
            evidence_type=row.evidence_type.value
            if hasattr(row.evidence_type, "value")
            else str(row.evidence_type),
            title=row.title,
            description=row.description,
            file_path=row.file_path,
            start_line=row.start_line,
            end_line=row.end_line,
        )
        for row in evidence_rows
    ]

    summary_narrative = None
    architectural_style = None
    if snapshot and snapshot.summary:
        try:
            summary_data = (
                json.loads(snapshot.summary)
                if isinstance(snapshot.summary, str)
                else snapshot.summary
            )
            summary_narrative = summary_data.get("narrative")
            architectural_style = summary_data.get("architectural_style")
        except Exception:
            pass

    requested_count = payload.num_questions if payload else 3
    q_input = QuestionGenerationInput(
        project_name=project.name,
        commit_hash=snapshot.commit_hash if snapshot else "HEAD",
        architectural_style=architectural_style,
        summary_narrative=summary_narrative,
        evidence_items=evidence_items,
        requested_count=requested_count,
    )

    q_response = await generate_grounded_questions(q_input)

    session = await create_defense_session(
        project_id=str(project_id),
        questions=q_response.questions,
    )

    logger.info(
        "defense_session_started",
        session_id=session.session_id,
        project_id=str(project_id),
        question_count=len(session.questions),
    )

    return session


@router.post(
    "/defense/sessions/{session_id}/answer",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate response to current defense question or stress-test",
    description=(
        "Submits candidate defense, evaluates technical depth, and advances "
        "the interview state machine through stress-test or mentor-guidance branches."
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


@router.get(
    "/defense/sessions/{session_id}/report",
    response_model=DefenseReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate and retrieve final architectural defense evaluation report",
)
async def get_defense_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DefenseReportResponse:
    """Generates structured evaluation report for a completed defense session."""
    session = await defense_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defense session '{session_id}' not found.",
        )

    # Multi-tenant isolation: verify user owns the project
    proj_stmt = select(Project).where(
        Project.id == uuid.UUID(session.project_id),
        Project.user_id == current_user.id,
    )
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    if session.status != DefenseStage.SESSION_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Defense session must be completed before report generation.",
        )

    return await generate_defense_report(session)
