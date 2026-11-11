"""FastAPI REST router for Stress Test & What-If Simulation Mode.

Endpoints:
  POST /api/v1/stress-test/projects/{project_id}/scenarios
  POST /api/v1/stress-test/projects/{project_id}/sessions/start
  GET  /api/v1/stress-test/sessions/{session_id}
  POST /api/v1/stress-test/sessions/{session_id}/respond
"""

import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.stress_test_generator import evaluate_stress_defense, generate_stress_scenarios
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.analysis import Dependency, Evidence
from app.models.project import Project, User
from app.schemas.stress_test import (
    GenerateStressScenariosRequest,
    StartStressDefenseRequest,
    StressDefenseSessionState,
    StressDefenseTurn,
    StressScenarioListResponse,
    StressSessionStage,
    SubmitStressAnswerRequest,
)
from app.services.stress_cache import (
    MAX_CACHED_SCENARIOS_PER_PROJECT,
    _active_view_state,
    _unfiltered_catalog_meta,
    cache_project_scenarios,
    clear_project_meta,
    get_cached_unfiltered_scenarios,
    project_stress_cache,
    record_active_view_seq,
    stress_session_store,
)

__all__ = [
    "MAX_CACHED_SCENARIOS_PER_PROJECT",
    "_active_view_state",
    "_unfiltered_catalog_meta",
    "project_stress_cache",
    "router",
    "stress_session_store",
]

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Stress Test / What-If Mode"])


async def _get_owned_project(
    project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Project:
    """Fetch a user-owned project or raise HTTP 404."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _gather_evidence_context(project_id: uuid.UUID, db: AsyncSession) -> List[dict]:
    """Collects evidence and dependencies for context grounding."""
    ev_stmt = select(Evidence).where(Evidence.project_id == project_id).limit(10)
    evidences = (await db.execute(ev_stmt)).scalars().all()
    items = [
        {"id": str(e.id), "file_path": e.file_path, "symbol_name": e.title, "type": e.evidence_type}
        for e in evidences
    ]
    dep_stmt = select(Dependency).where(Dependency.project_id == project_id).limit(10)
    deps = (await db.execute(dep_stmt)).scalars().all()
    items.extend(
        {"id": str(d.id), "file_path": "manifest", "symbol_name": d.name, "type": "dependency"}
        for d in deps
    )
    return items


@router.post(
    "/projects/{project_id}/scenarios",
    response_model=StressScenarioListResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or catalog scaling stress test scenarios for a project",
)
async def get_or_generate_stress_scenarios(
    project_id: uuid.UUID,
    payload: Optional[GenerateStressScenariosRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StressScenarioListResponse:
    """Returns scaling scenarios grounded in repository architecture evidence."""
    project = await _get_owned_project(project_id, current_user.id, db)

    req = payload or GenerateStressScenariosRequest()
    if project_id not in project_stress_cache:
        clear_project_meta(project_id)

    has_view = req.view_id is not None and req.request_seq is not None
    view_id, req_seq = req.view_id or "", req.request_seq or 0
    if has_view and not record_active_view_seq(project_id, view_id, req_seq):
        return StressScenarioListResponse(
            project_id=str(project_id), total_scenarios=0, scenarios=[]
        )

    scenarios = (
        get_cached_unfiltered_scenarios(project_id, req.max_scenarios)
        if not req.constraint_type
        else None
    )
    if scenarios is not None:
        if has_view:
            record_active_view_seq(project_id, view_id, req_seq, {s.id for s in scenarios})
    else:
        evidence_items = await _gather_evidence_context(project_id, db)
        scenarios = await generate_stress_scenarios(
            project_name=project.name,
            evidence_items=evidence_items,
            constraint_type=req.constraint_type,
            max_scenarios=req.max_scenarios,
            model=req.model,
            api_key=req.api_key,
            base_url=req.base_url,
        )
        is_current = (
            record_active_view_seq(project_id, view_id, req_seq, {s.id for s in scenarios})
            if has_view
            else True
        )
        if is_current:
            cache_project_scenarios(
                project_id,
                scenarios,
                is_unfiltered=req.constraint_type is None,
                requested_limit=req.max_scenarios,
            )

    return StressScenarioListResponse(
        project_id=str(project_id), total_scenarios=len(scenarios), scenarios=scenarios
    )


@router.post(
    "/projects/{project_id}/sessions/start",
    response_model=StressDefenseSessionState,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate an interactive scaling defense session",
)
async def start_stress_defense_session(
    project_id: uuid.UUID,
    payload: StartStressDefenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StressDefenseSessionState:
    """Launches an interactive what-if defense session for a chosen scenario."""
    await _get_owned_project(project_id, current_user.id, db)
    cached_list = project_stress_cache.get(project_id, [])
    target_scenario = next((s for s in cached_list if s.id == payload.scenario_id), None)
    if not target_scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stress scenario '{payload.scenario_id}' not found. Generate scenarios first.",
        )

    session_id = str(uuid.uuid4())
    initial_turn = StressDefenseTurn(
        role="interviewer",
        content=(
            f"Scaling Challenge: {target_scenario.title}\n\n"
            f"Scenario Constraint: {target_scenario.context_description}\n\n"
            f"Principal Architect Question:\n{target_scenario.hypothetical_prompt}"
        ),
        stage=StressSessionStage.SCENARIO_ACTIVE,
        metadata={"constraint_type": target_scenario.constraint_type.value},
    )
    session = StressDefenseSessionState(
        session_id=session_id,
        project_id=str(project_id),
        scenario=target_scenario,
        stage=StressSessionStage.SCENARIO_ACTIVE,
        turns=[initial_turn],
    )
    stress_session_store[session_id] = session
    logger.info("stress_defense_session_started", session_id=session_id, project_id=str(project_id))
    return session


@router.get(
    "/sessions/{session_id}",
    response_model=StressDefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Retrieve active stress defense session state",
)
async def get_stress_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> StressDefenseSessionState:
    """Returns the current transcript, progress, and scores for a stress defense session."""
    session = stress_session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post(
    "/sessions/{session_id}/respond",
    response_model=StressDefenseSessionState,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate response to scaling constraint challenge",
)
async def submit_stress_defense_turn(
    session_id: str,
    payload: SubmitStressAnswerRequest,
    current_user: User = Depends(get_current_user),
) -> StressDefenseSessionState:
    """Evaluates candidate scaling mitigation and advances interview stage."""
    session = stress_session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.stage == StressSessionStage.COMPLETED:
        raise HTTPException(status_code=400, detail="Session is already completed")

    session.turns.append(
        StressDefenseTurn(role="candidate", content=payload.answer, stage=session.stage)
    )
    eval_out = await evaluate_stress_defense(
        scenario=session.scenario,
        candidate_answer=payload.answer,
        stage=session.stage,
        model=payload.model,
        api_key=payload.api_key,
        base_url=payload.base_url,
    )

    if (
        session.stage == StressSessionStage.SCENARIO_ACTIVE
        and eval_out.follow_up_constraint
        and not eval_out.is_terminal
    ):
        session.stage = StressSessionStage.FOLLOW_UP_CONSTRAINED
        session.current_turn_index += 1
        session.turns.append(
            StressDefenseTurn(
                role="interviewer",
                content=(
                    f"Defense Evaluation: {eval_out.feedback}\n\n"
                    f"Secondary Constraint:\n{eval_out.follow_up_constraint}"
                ),
                stage=StressSessionStage.FOLLOW_UP_CONSTRAINED,
                metadata={"depth_score": eval_out.depth_score},
            )
        )
    else:
        session.stage = StressSessionStage.COMPLETED
        session.overall_score = float(eval_out.depth_score)
        session.bottleneck_identified = eval_out.bottleneck_identified
        session.feedback = eval_out.feedback
        session.turns.append(
            StressDefenseTurn(
                role="system",
                content=(
                    f"Stress Defense Concluded. Score: {eval_out.depth_score}/10.\n"
                    f"Feedback: {eval_out.feedback}"
                ),
                stage=StressSessionStage.COMPLETED,
                metadata={
                    "overall_score": eval_out.depth_score,
                    "scaling_sound": eval_out.scaling_strategy_sound,
                    "tradeoffs_acknowledged": eval_out.tradeoffs_acknowledged,
                },
            )
        )

    return session
