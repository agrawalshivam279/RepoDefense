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
from app.schemas.report import DefenseReportResponse, EnhancedDefenseReportResponse
from app.services.enhanced_report import generate_enhanced_defense_report

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Defense"])


def _parse_snapshot_summary(
    snapshot: Optional[RepositorySnapshot],
) -> tuple[Optional[str], Optional[str]]:
    """Extracts optional narrative and architectural style from a snapshot summary."""
    if not snapshot or not snapshot.summary:
        return None, None
    try:
        data = json.loads(snapshot.summary)
        if isinstance(data, dict):
            return data.get("narrative"), data.get("architectural_style")
    except Exception:
        return snapshot.summary, None
    return None, None


async def _get_authorized_session(
    session_id: str,
    current_user: User,
    db: AsyncSession,
    require_completed: bool = False,
) -> DefenseSessionState:
    """Validates session existence, project ownership, and optional completion status."""
    session = await defense_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defense session '{session_id}' not found.",
        )

    try:
        project_uuid = uuid.UUID(session.project_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid project ID '{session.project_id}'.",
        )

    proj_stmt = select(Project).where(
        Project.id == project_uuid,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    if require_completed and session.status != DefenseStage.SESSION_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Defense session must be completed before report generation.",
        )

    return session


@router.post(
    "/projects/{project_id}/defense/start",
    response_model=DefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Start an evidence-grounded defense session for a repository",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    snap_stmt = (
        select(RepositorySnapshot)
        .where(RepositorySnapshot.project_id == project_id)
        .order_by(RepositorySnapshot.created_at.desc())
    )
    snapshot = (await db.execute(snap_stmt)).scalars().first()

    evidence_stmt = select(Evidence).where(Evidence.project_id == project_id)
    filtered_rows = []
    if payload and payload.custom_categories:
        cat_stmt = (
            evidence_stmt.where(Evidence.evidence_type.in_(payload.custom_categories))
            .order_by(Evidence.id)
            .limit(10)
        )
        filtered_rows = (await db.execute(cat_stmt)).scalars().all()

    evidence_rows = filtered_rows or (
        await db.execute(evidence_stmt.order_by(Evidence.id).limit(10))
    ).scalars().all()

    evidence_pool: list[EvidenceRef] = [
        EvidenceRef(
            id=str(row.id),
            evidence_type=row.evidence_type,
            title=row.title,
            description=row.description,
            file_path=row.file_path,
            start_line=row.start_line,
            end_line=row.end_line,
        )
        for row in evidence_rows
    ]

    narrative, style = _parse_snapshot_summary(snapshot)
    input_payload = QuestionGenerationInput(
        project_name=project.name,
        summary_narrative=narrative,
        architectural_style=style,
        evidence_items=evidence_pool,
        requested_count=payload.num_questions if payload else 3,
    )

    try:
        questions = await generate_grounded_questions(
            input_data=input_payload,
            model=payload.model if payload else None,
            api_key=payload.api_key if payload else None,
            base_url=payload.base_url if payload else None,
        )
    except Exception as exc:
        logger.error(
            "defense_question_generation_failed",
            project_id=str(project_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate questions: {str(exc)}",
        ) from exc

    return await create_defense_session(project_id=str(project_id), questions=questions)


@router.post(
    "/defense/sessions/{session_id}/answer",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/defense/sessions/{session_id}/turn",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate defense answer and evaluate progress",
)
async def submit_defense_turn_endpoint(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DefenseSessionState:
    """Processes candidate defense turn, triggers rubric evaluation, and advances FSM."""
    session = await _get_authorized_session(session_id, current_user, db)

    if session.status == DefenseStage.SESSION_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Defense session is already completed.",
        )

    try:
        updated_session = await submit_defense_turn(
            session_id=session_id,
            candidate_answer=payload.answer,
            model=payload.model,
            api_key=payload.api_key,
            base_url=payload.base_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("defense_turn_submission_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate defense turn.",
        ) from exc

    return updated_session


@router.get(
    "/defense/sessions/{session_id}",
    response_model=DefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current state of a defense interview session",
)
async def get_defense_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DefenseSessionState:
    """Retrieves current interview state, transcript, and scores for an authorized session."""
    return await _get_authorized_session(session_id, current_user, db)


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
    session = await _get_authorized_session(
        session_id, current_user, db, require_completed=True
    )
    return await generate_defense_report(session)


@router.get(
    "/defense/sessions/{session_id}/enhanced-report",
    response_model=EnhancedDefenseReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate and retrieve enhanced architectural defense report",
)
async def get_enhanced_defense_report_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnhancedDefenseReportResponse:
    """Generates enhanced architectural report for a completed defense session."""
    session = await _get_authorized_session(
        session_id, current_user, db, require_completed=True
    )
    return await generate_enhanced_defense_report(session, db)
