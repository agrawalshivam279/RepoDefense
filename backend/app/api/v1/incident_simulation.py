"""FastAPI REST router for Chaos Engineering & Incident Simulation.

Endpoints:
  POST /api/v1/incident-simulation/projects/{project_id}/scenarios
  POST /api/v1/incident-simulation/projects/{project_id}/sessions/start
  GET  /api/v1/incident-simulation/sessions/{session_id}
  POST /api/v1/incident-simulation/sessions/{session_id}/respond
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.incident_generator import (
    evaluate_incident_defense_turn,
    generate_incident_scenarios,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.analysis import Dependency, Evidence
from app.models.project import Project, User
from app.schemas.incident import (
    GenerateScenariosRequest,
    IncidentDefenseSessionState,
    IncidentDefenseTurn,
    IncidentScenario,
    IncidentStage,
    ScenarioListResponse,
    StartIncidentDefenseRequest,
    SubmitIncidentAnswerRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Incident Simulation"])

# In-memory store for active incident defense sessions (production would sync to Redis)
incident_session_store: Dict[uuid.UUID, IncidentDefenseSessionState] = {}
# Cached scenarios catalog per project
project_scenarios_cache: Dict[uuid.UUID, List[IncidentScenario]] = {}


async def _gather_project_evidence(project_id: uuid.UUID, db: AsyncSession) -> List[dict]:
    """Collect evidence and dependencies for context grounding."""
    evidence_items: List[dict] = []

    ev_stmt = select(Evidence).where(Evidence.project_id == project_id).limit(10)
    evidences = (await db.execute(ev_stmt)).scalars().all()
    for e in evidences:
        evidence_items.append(
            {"file_path": e.file_path, "symbol_name": e.title, "type": e.evidence_type}
        )

    dep_stmt = select(Dependency).where(Dependency.project_id == project_id).limit(10)
    deps = (await db.execute(dep_stmt)).scalars().all()
    for d in deps:
        evidence_items.append(
            {
                "file_path": d.source_file or "package.json",
                "symbol_name": d.name,
                "type": "dependency",
            }
        )

    return evidence_items


@router.post(
    "/projects/{project_id}/scenarios",
    response_model=ScenarioListResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate chaos incident scenarios for a project",
)
async def generate_scenarios_endpoint(
    project_id: uuid.UUID,
    payload: GenerateScenariosRequest = GenerateScenariosRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioListResponse:
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    evidence_items = await _gather_project_evidence(project_id, db)
    scenarios = await generate_incident_scenarios(
        evidence_items=evidence_items,
        category=payload.category,
        limit=payload.limit,
    )
    project_scenarios_cache[project_id] = scenarios

    return ScenarioListResponse(
        project_id=project_id,
        total_scenarios=len(scenarios),
        scenarios=scenarios,
    )


@router.post(
    "/projects/{project_id}/sessions/start",
    response_model=IncidentDefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Start an interactive incident defense session",
)
async def start_incident_session_endpoint(
    project_id: uuid.UUID,
    payload: StartIncidentDefenseRequest = StartIncidentDefenseRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentDefenseSessionState:
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    selected_scenario: IncidentScenario | None = None
    cached = project_scenarios_cache.get(project_id, [])

    if payload.scenario_id:
        selected_scenario = next((s for s in cached if s.id == payload.scenario_id), None)

    if not selected_scenario:
        evidence_items = await _gather_project_evidence(project_id, db)
        fresh_scenarios = await generate_incident_scenarios(
            evidence_items=evidence_items,
            category=payload.category,
            limit=1,
        )
        selected_scenario = fresh_scenarios[0]

    session_id = uuid.uuid4()
    initial_turn = IncidentDefenseTurn(
        turn_index=1,
        prompt=selected_scenario.incident_question,
    )

    state = IncidentDefenseSessionState(
        id=session_id,
        project_id=project_id,
        scenario=selected_scenario,
        turns=[initial_turn],
        current_turn_index=1,
        max_turns=3,
        stage=IncidentStage.TRIAGE,
    )

    incident_session_store[session_id] = state
    logger.info(
        "Incident defense session started",
        session_id=str(session_id),
        scenario=selected_scenario.title,
    )
    return state


@router.get(
    "/sessions/{session_id}",
    response_model=IncidentDefenseSessionState,
    summary="Get incident defense session state",
)
async def get_incident_session_endpoint(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentDefenseSessionState:
    session = incident_session_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident session not found"
        )

    stmt = select(Project).where(
        Project.id == session.project_id, Project.user_id == current_user.id
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return session


@router.post(
    "/sessions/{session_id}/respond",
    response_model=IncidentDefenseSessionState,
    summary="Respond to active incident turn",
)
async def respond_to_incident_turn_endpoint(
    session_id: uuid.UUID,
    payload: SubmitIncidentAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentDefenseSessionState:
    session = incident_session_store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident session not found"
        )

    stmt = select(Project).where(
        Project.id == session.project_id, Project.user_id == current_user.id
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if session.stage == IncidentStage.POSTMORTEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident defense session is already completed and in postmortem.",
        )

    eval_result = evaluate_incident_defense_turn(
        scenario=session.scenario,
        turn_index=session.current_turn_index,
        max_turns=session.max_turns,
        candidate_answer=payload.answer,
    )

    current_turn = session.turns[session.current_turn_index - 1]
    current_turn.candidate_answer = payload.answer
    current_turn.score = eval_result["score"]
    current_turn.feedback = eval_result["feedback"]
    current_turn.escalation_injected = eval_result.get("escalation_injected")

    if session.current_turn_index < session.max_turns:
        session.current_turn_index += 1
        session.stage = eval_result["next_stage"]
        next_turn = IncidentDefenseTurn(
            turn_index=session.current_turn_index,
            prompt=eval_result["next_prompt"],
        )
        session.turns.append(next_turn)
    else:
        session.stage = IncidentStage.POSTMORTEM
        scores = [t.score for t in session.turns if t.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        session.overall_score = avg_score
        session.postmortem_summary = (
            f"INCIDENT POSTMORTEM SUMMARY: {session.scenario.title} successfully resolved "
            f"with overall resilience score of {avg_score}/100. The candidate navigated from "
            "initial triage to cascading chaos mitigation and established robust safeguards."
        )

    session.updated_at = datetime.now(timezone.utc).isoformat()
    incident_session_store[session_id] = session
    logger.info(
        "Incident turn evaluated",
        session_id=str(session_id),
        turn=session.current_turn_index,
        stage=session.stage,
    )
    return session
