"""FastAPI REST router for Stress Test & What-If Simulation Mode.

Endpoints:
  POST /api/v1/stress-test/projects/{project_id}/scenarios
  POST /api/v1/stress-test/projects/{project_id}/sessions/start
  GET  /api/v1/stress-test/sessions/{session_id}
  POST /api/v1/stress-test/sessions/{session_id}/respond
"""

import uuid
from typing import Dict, List, Optional, Set, Tuple

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
    StressTestScenario,
    SubmitStressAnswerRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Stress Test / What-If Mode"])

stress_session_store: Dict[str, StressDefenseSessionState] = {}
project_stress_cache: Dict[uuid.UUID, List[StressTestScenario]] = {}
_unfiltered_catalog_meta: Dict[uuid.UUID, Tuple[int, Set[str]]] = {}


def _cache_project_scenarios(
    project_id: uuid.UUID,
    scenarios: List[StressTestScenario],
    *,
    is_unfiltered: bool,
    requested_limit: int,
) -> None:
    """Merge generated scenarios into project cache and record unfiltered catalog IDs."""
    existing = {s.id: s for s in project_stress_cache.get(project_id, [])}
    for scenario in scenarios:
        existing[scenario.id] = scenario
    project_stress_cache[project_id] = list(existing.values())
    if is_unfiltered:
        _unfiltered_catalog_meta[project_id] = (requested_limit, {s.id for s in scenarios})


async def _gather_evidence_context(project_id: uuid.UUID, db: AsyncSession) -> List[dict]:
    """Collects evidence and dependencies for context grounding."""
    items: List[dict] = []
    ev_stmt = select(Evidence).where(Evidence.project_id == project_id).limit(10)
    evidences = (await db.execute(ev_stmt)).scalars().all()
    for e in evidences:
        items.append(
            {
                "id": str(e.id),
                "file_path": e.file_path,
                "symbol_name": e.title,
                "type": e.evidence_type,
            }
        )

    dep_stmt = select(Dependency).where(Dependency.project_id == project_id).limit(10)
    deps = (await db.execute(dep_stmt)).scalars().all()
    for d in deps:
        items.append(
            {"id": str(d.id), "file_path": "manifest", "symbol_name": d.name, "type": "dependency"}
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
    proj_stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    req = payload or GenerateStressScenariosRequest()
    if project_id not in project_stress_cache:
        _unfiltered_catalog_meta.pop(project_id, None)

    cached_catalog = project_stress_cache.get(project_id)
    unfiltered_meta = _unfiltered_catalog_meta.get(project_id)
    cached_unfiltered: Optional[List[StressTestScenario]] = None
    if not req.constraint_type and cached_catalog is not None and unfiltered_meta is not None:
        prev_limit, unfiltered_ids = unfiltered_meta
        matched = [s for s in cached_catalog if s.id in unfiltered_ids]
        if prev_limit >= req.max_scenarios or len(matched) >= req.max_scenarios:
            cached_unfiltered = matched[: req.max_scenarios]

    if cached_unfiltered is not None:
        scenarios = cached_unfiltered
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
        _cache_project_scenarios(
            project_id,
            scenarios,
            is_unfiltered=req.constraint_type is None,
            requested_limit=req.max_scenarios,
        )

    return StressScenarioListResponse(
        project_id=str(project_id),
        total_scenarios=len(scenarios),
        scenarios=scenarios,
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
    proj_stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

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
        current_turn_index=0,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session is already completed"
        )

    cand_turn = StressDefenseTurn(
        role="candidate",
        content=payload.answer,
        stage=session.stage,
    )
    session.turns.append(cand_turn)

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
        interviewer_turn = StressDefenseTurn(
            role="interviewer",
            content=(
                f"Defense Evaluation: {eval_out.feedback}\n\n"
                f"Secondary Constraint:\n{eval_out.follow_up_constraint}"
            ),
            stage=StressSessionStage.FOLLOW_UP_CONSTRAINED,
            metadata={"depth_score": eval_out.depth_score},
        )
        session.turns.append(interviewer_turn)
    else:
        session.stage = StressSessionStage.COMPLETED
        session.overall_score = float(eval_out.depth_score)
        session.bottleneck_identified = eval_out.bottleneck_identified
        session.feedback = eval_out.feedback
        sys_turn = StressDefenseTurn(
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
        session.turns.append(sys_turn)

    return session
