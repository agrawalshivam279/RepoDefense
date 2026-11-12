"""FastAPI REST router for Architecture Defense Mode."""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

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
    ArchDefenseEvaluationOutput,
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
from app.services.architecture import detect_repository_architecture
from app.services.diagram import generate_project_architecture_diagram

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Architecture Defense Mode"])

MAX_CACHED_PROJECTS = 100
MAX_CACHED_TOPICS_PER_PROJECT = 50
MAX_ACTIVE_SESSIONS = 500


@dataclass
class _ProjectCatalogEntry:
    fingerprint: str
    report: ArchitectureReportResponse
    diagram: DiagramResponse
    topics: Dict[str, ArchDefenseTopic] = field(default_factory=dict)
    unfiltered_ids: List[str] = field(default_factory=list)


_arch_topic_catalog: Dict[uuid.UUID, _ProjectCatalogEntry] = {}
_arch_session_store: Dict[str, Tuple[uuid.UUID, ArchDefenseSessionState]] = {}


def _compute_arch_fingerprint(project: Project, report: ArchitectureReportResponse) -> str:
    """Compute a deterministic fingerprint from project state and static architecture scan."""
    status_val = getattr(project, "status", "")
    status_str = status_val.value if hasattr(status_val, "value") else str(status_val or "")
    parts = [
        status_str,
        str(getattr(project, "updated_at", "") or ""),
        str(report.total_files_analyzed),
        report.primary_pattern.pattern_type.value,
        f"{report.primary_pattern.confidence_score:.3f}",
        *[f"{r.title}:{r.severity}" for r in report.architectural_risks],
        *[f"{k}={v}" for k, v in sorted(report.directory_summary.items())],
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _store_topics_bounded(
    entry: _ProjectCatalogEntry, topics: List[ArchDefenseTopic], set_unfiltered: bool
) -> None:
    """Retain generated topics cleanly while keeping per-project memory bounded."""
    keep_ids = {t.id for t in topics}
    for topic in topics:
        entry.topics[topic.id] = topic
    while len(entry.topics) > MAX_CACHED_TOPICS_PER_PROJECT:
        oldest_id = next(iter(entry.topics))
        if oldest_id in keep_ids:
            break
        entry.topics.pop(oldest_id, None)
    if set_unfiltered:
        entry.unfiltered_ids = [t.id for t in topics]


async def _get_owned_project(
    project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Project:
    """Fetch a user-owned project or raise HTTP 404."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_owned_session(session_id: str, user_id: uuid.UUID) -> ArchDefenseSessionState:
    """Fetch a session owned by current_user or raise HTTP 404 (prevents IDOR)."""
    record = _arch_session_store.get(session_id)
    if not record or record[0] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return record[1]


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


def _advance_session_fsm(
    session: ArchDefenseSessionState, eval_out: ArchDefenseEvaluationOutput
) -> None:
    """Apply deterministic FSM transition after scoring a candidate defense turn."""
    session.updated_at = datetime.now(timezone.utc).isoformat()
    if (
        session.stage == ArchDefenseStage.TOPIC_ACTIVE
        and eval_out.follow_up_challenge and not eval_out.is_terminal
    ):
        session.stage = ArchDefenseStage.TRADEOFF_CHALLENGE
        session.current_turn_index += 1
        session.turns.append(
            ArchDefenseTurn(
                role="interviewer", stage=ArchDefenseStage.TRADEOFF_CHALLENGE,
                content=(
                    f"Architectural Assessment: {eval_out.feedback}\n\n"
                    f"Tradeoff Challenge:\n{eval_out.follow_up_challenge}"
                ),
                metadata={
                    "depth_score": eval_out.depth_score,
                    "boundary_coherence_score": eval_out.boundary_coherence_score,
                },
            )
        )
        return

    session.stage = ArchDefenseStage.COMPLETED
    avg = (eval_out.depth_score + eval_out.boundary_coherence_score) / 2.0
    session.overall_score = round(avg, 1)
    session.pattern_rationale_solid = eval_out.pattern_rationale_solid
    session.boundary_coherence_score = eval_out.boundary_coherence_score
    session.feedback = eval_out.feedback
    session.turns.append(
        ArchDefenseTurn(
            role="system", stage=ArchDefenseStage.COMPLETED,
            content=(
                f"Architecture Defense Concluded. Score: {session.overall_score}/10.\n"
                f"Feedback: {eval_out.feedback}"
            ),
            metadata={
                "overall_score": session.overall_score, "depth_score": eval_out.depth_score,
                "boundary_coherence_score": eval_out.boundary_coherence_score,
                "pattern_rationale_solid": eval_out.pattern_rationale_solid,
                "tradeoffs_articulated": eval_out.tradeoffs_articulated,
            },
        )
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

    report = await detect_repository_architecture(project, db)
    fingerprint = _compute_arch_fingerprint(project, report)

    entry = _arch_topic_catalog.get(project_id)
    if entry is not None and entry.fingerprint != fingerprint:
        _arch_topic_catalog.pop(project_id, None)
        entry = None

    if not has_override and entry is not None and req.focus_area is None:
        if len(entry.unfiltered_ids) >= req.max_topics:
            cached = [entry.topics[tid] for tid in entry.unfiltered_ids[: req.max_topics]
                      if tid in entry.topics]
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

    if entry is None:
        while len(_arch_topic_catalog) >= MAX_CACHED_PROJECTS:
            _arch_topic_catalog.pop(next(iter(_arch_topic_catalog)), None)
        entry = _ProjectCatalogEntry(fingerprint=fingerprint, report=report, diagram=diagram)
        _arch_topic_catalog[project_id] = entry
    elif not has_override:
        entry.report, entry.diagram = report, diagram

    keep_unfiltered = not has_override and req.focus_area is None
    _store_topics_bounded(entry, topics, set_unfiltered=keep_unfiltered)
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
    await _get_owned_project(project_id, current_user.id, db)
    entry = _arch_topic_catalog.get(project_id)
    target_topic = entry.topics.get(payload.topic_id) if entry else None
    if not target_topic or not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Architecture defense topic not found"
        )

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
        mermaid_code=entry.diagram.mermaid_code, diagram_summary=entry.diagram.summary,
        primary_pattern_name=entry.report.primary_pattern.pattern_name,
        stage=ArchDefenseStage.TOPIC_ACTIVE, turns=[initial_turn],
    )
    while len(_arch_session_store) >= MAX_ACTIVE_SESSIONS:
        _arch_session_store.pop(next(iter(_arch_session_store)), None)
    _arch_session_store[session_id] = (current_user.id, session)
    logger.info("arch_defense_session_started", session_id=session_id, project_id=str(project_id))
    return session


@router.get("/sessions/{session_id}", response_model=ArchDefenseSessionState)
async def get_arch_defense_session(
    session_id: str, current_user: User = Depends(get_current_user),
) -> ArchDefenseSessionState:
    """Return current dialogue transcript, diagram code, and scoring state."""
    return _get_owned_session(session_id, current_user.id)


@router.post("/sessions/{session_id}/respond", response_model=ArchDefenseSessionState)
async def submit_arch_defense_turn(
    session_id: str, payload: SubmitArchAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> ArchDefenseSessionState:
    """Evaluate candidate design rationale and advance the FSM stage."""
    session = _get_owned_session(session_id, current_user.id)
    if session.stage == ArchDefenseStage.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session is already completed"
        )
    session.turns.append(
        ArchDefenseTurn(role="candidate", content=payload.answer, stage=session.stage)
    )
    eval_out = await evaluate_arch_defense(
        topic=session.topic, candidate_answer=payload.answer, stage=session.stage,
        model=payload.model, api_key=payload.api_key, base_url=payload.base_url,
    )
    _advance_session_fsm(session, eval_out)
    return session
