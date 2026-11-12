"""FastAPI REST router for Architecture Defense Mode."""

import asyncio
import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.arch_defense_generator import (
    evaluate_arch_defense,
    generate_arch_defense_topics,
    resolve_llm_credentials,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.arch_defense import (
    ArchDefenseSessionState,
    ArchDefenseStage,
    ArchDefenseTopic,
    ArchDefenseTurn,
    ArchTopicListResponse,
    GenerateArchTopicsRequest,
    StartArchDefenseRequest,
    SubmitArchAnswerRequest,
)
from app.schemas.architecture import ArchitectureReportResponse
from app.schemas.diagram import DiagramResponse
from app.services.arch_defense_store import (
    MAX_CACHED_PROJECTS,
    ProjectCatalogEntry,
    advance_session_fsm,
    compute_arch_fingerprint,
    ensure_session_capacity,
    get_owned_session,
    store_topics_bounded,
)
from app.services.arch_defense_store import (
    arch_session_store as _arch_session_store,
)
from app.services.arch_defense_store import (
    arch_topic_catalog as _arch_topic_catalog,
)
from app.services.arch_defense_store import (
    project_locks as _project_locks,
)
from app.services.arch_defense_store import (
    session_locks as _session_locks,
)
from app.services.architecture import detect_repository_architecture
from app.services.diagram import generate_project_architecture_diagram

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Architecture Defense Mode"])


async def _get_owned_project(
    project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Project:
    """Fetch a user-owned project or raise HTTP 404."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _build_topic_response(
    project: Project, report: ArchitectureReportResponse, diagram: DiagramResponse,
    topics: List[ArchDefenseTopic],
) -> ArchTopicListResponse:
    return ArchTopicListResponse(
        project_id=str(project.id), project_name=project.name,
        primary_pattern=report.primary_pattern, diagram_type=diagram.diagram_type,
        mermaid_code=diagram.mermaid_code, nodes=diagram.nodes, edges=diagram.edges,
        is_diagram_fallback=diagram.is_fallback, total_topics=len(topics), topics=topics,
    )


@router.post("/projects/{project_id}/topics", response_model=ArchTopicListResponse)
async def get_or_generate_arch_topics(
    project_id: uuid.UUID, payload: Optional[GenerateArchTopicsRequest] = None,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ArchTopicListResponse:
    """Synthesize high-level architecture defense topics backed by diagram & pattern analysis."""
    project = await _get_owned_project(project_id, current_user.id, db)
    req = payload or GenerateArchTopicsRequest()
    has_override = any(v is not None for v in (req.model, req.api_key, req.base_url))

    proj_lock = _project_locks.setdefault(project_id, asyncio.Lock())
    async with proj_lock:
        report = await detect_repository_architecture(project, db)
        fingerprint = compute_arch_fingerprint(project, report)

        entry = _arch_topic_catalog.get(project_id)
        if entry is not None and entry.fingerprint != fingerprint:
            _arch_topic_catalog.pop(project_id, None)
            entry = None

        if not has_override and entry is not None and req.focus_area is None:
            if len(entry.unfiltered_ids) >= req.max_topics:
                cached = [
                    entry.topics[tid].topic for tid in entry.unfiltered_ids[: req.max_topics]
                    if tid in entry.topics
                ]
                if len(cached) == req.max_topics:
                    return _build_topic_response(project, entry.report, entry.diagram, cached)

        diag_creds = resolve_llm_credentials(req.api_key, req.base_url)
        diagram = await generate_project_architecture_diagram(
            project=project, db=db, model=req.model,
            api_key=diag_creds[0] if diag_creds else "",
            base_url=diag_creds[1] if diag_creds and req.base_url is not None else None,
        )
        topics = await generate_arch_defense_topics(
            report=report, diagram=diagram, focus_area=req.focus_area, max_topics=req.max_topics,
            model=req.model, api_key=req.api_key, base_url=req.base_url,
        )

        entry = _arch_topic_catalog.get(project_id)
        if entry is not None and entry.fingerprint != fingerprint:
            _arch_topic_catalog.pop(project_id, None)
            entry = None
        if entry is None:
            while len(_arch_topic_catalog) >= MAX_CACHED_PROJECTS:
                evicted_pid = next(iter(_arch_topic_catalog))
                _arch_topic_catalog.pop(evicted_pid, None)
                _project_locks.pop(evicted_pid, None)
            entry = ProjectCatalogEntry(fingerprint=fingerprint, report=report, diagram=diagram)
            _arch_topic_catalog[project_id] = entry

        keep_unfiltered = not has_override and req.focus_area is None
        store_topics_bounded(entry, topics, report, diagram, set_unfiltered=keep_unfiltered)
        return _build_topic_response(project, report, diagram, topics)


@router.post(
    "/projects/{project_id}/sessions/start",
    response_model=ArchDefenseSessionState,
    status_code=status.HTTP_201_CREATED,
)
async def start_arch_defense_session(
    project_id: uuid.UUID, payload: StartArchDefenseRequest,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ArchDefenseSessionState:
    """Initialize a stateful Principal Architect defense session for the chosen topic."""
    if any(v is not None for v in (payload.model, payload.api_key, payload.base_url)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM overrides are not supported on session start; supply them on /respond.",
        )
    await _get_owned_project(project_id, current_user.id, db)
    entry = _arch_topic_catalog.get(project_id)
    cached_rec = entry.topics.get(payload.topic_id) if entry else None
    if not cached_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Architecture defense topic not found"
        )

    ensure_session_capacity(user_id=current_user.id)
    target_topic = cached_rec.topic
    session_id = str(uuid.uuid4())
    initial_turn = ArchDefenseTurn(
        role="interviewer", content=target_topic.interrogation_prompt,
        stage=ArchDefenseStage.TOPIC_ACTIVE,
        metadata={
            "focus_area": target_topic.focus_area.value,
            "target_node_ids": [n.node_id for n in target_topic.target_nodes],
        },
    )
    session = ArchDefenseSessionState(
        session_id=session_id, project_id=str(project_id), topic=target_topic,
        mermaid_code=cached_rec.diagram.mermaid_code, diagram_summary=cached_rec.diagram.summary,
        primary_pattern_name=cached_rec.report.primary_pattern.pattern_name,
        stage=ArchDefenseStage.TOPIC_ACTIVE, turns=[initial_turn],
    )
    _arch_session_store[session_id] = (current_user.id, session)
    logger.info("arch_defense_session_started", session_id=session_id, project_id=str(project_id))
    return session


@router.get("/sessions/{session_id}", response_model=ArchDefenseSessionState)
async def get_arch_defense_session(
    session_id: str, current_user: User = Depends(get_current_user),
) -> ArchDefenseSessionState:
    """Return current dialogue transcript, diagram code, and scoring state."""
    return get_owned_session(session_id, current_user.id)


@router.post("/sessions/{session_id}/respond", response_model=ArchDefenseSessionState)
async def submit_arch_defense_turn(
    session_id: str, payload: SubmitArchAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> ArchDefenseSessionState:
    """Serialize session turn evaluation and apply atomic FSM advancement."""
    get_owned_session(session_id, current_user.id)
    lock = _session_locks.setdefault(session_id, asyncio.Lock())
    async with lock:
        session = get_owned_session(session_id, current_user.id)
        if session.stage == ArchDefenseStage.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Session is already completed"
            )
        stage_before = session.stage
        turn_idx_before = session.current_turn_index
        eval_out = await evaluate_arch_defense(
            topic=session.topic, candidate_answer=payload.answer, stage=stage_before,
            model=payload.model, api_key=payload.api_key, base_url=payload.base_url,
        )
        if session.stage != stage_before or session.current_turn_index != turn_idx_before:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Session state changed mid-evaluation"
            )
        candidate_turn = ArchDefenseTurn(
            role="candidate", content=payload.answer, stage=stage_before
        )
        advance_session_fsm(session, eval_out, candidate_turn=candidate_turn)
        return session
