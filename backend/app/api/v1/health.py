"""Simulation readiness and operational health diagnostic endpoints."""

from fastapi import APIRouter

from app.ai.fsm import defense_store
from app.api.v1.incident_simulation import incident_session_store
from app.core.config import settings
from app.schemas.health import (
    SimulationModeStatus,
    SimulationReadinessResponse,
    StoreTelemetry,
)
from app.services.arch_defense_store import arch_session_store
from app.services.stress_cache import stress_session_store

router = APIRouter(tags=["Health"])


@router.get("/simulations", response_model=SimulationReadinessResponse)
async def get_simulation_readiness() -> SimulationReadinessResponse:
    """Returns operational readiness and active session metrics across all simulation engines."""
    fsm_sessions = list(defense_store._sessions.values())
    pr_count = sum(
        1 for s in fsm_sessions if any("diff" in (t.metadata or {}) for t in s.turns)
    )
    commit_count = sum(
        1 for s in fsm_sessions if any("commit" in (t.metadata or {}) for t in s.turns)
    )
    core_count = max(0, len(fsm_sessions) - pr_count - commit_count)

    incident_count = len(incident_session_store)
    stress_count = len(stress_session_store)
    arch_count = len(arch_session_store)

    modes = {
        "core_defense": SimulationModeStatus(
            mode="core_defense",
            display_name="Core Oral Defense",
            status="operational",
            active_sessions=core_count,
            capacity_limit=None,
        ),
        "pr_defense": SimulationModeStatus(
            mode="pr_defense",
            display_name="Pull Request Defense",
            status="operational",
            active_sessions=pr_count,
            capacity_limit=None,
        ),
        "commit_defense": SimulationModeStatus(
            mode="commit_defense",
            display_name="Git Commit Defense",
            status="operational",
            active_sessions=commit_count,
            capacity_limit=None,
        ),
        "incident_simulation": SimulationModeStatus(
            mode="incident_simulation",
            display_name="Incident Simulation War Room",
            status="operational",
            active_sessions=incident_count,
            capacity_limit=incident_session_store._max_items,
        ),
        "stress_test": SimulationModeStatus(
            mode="stress_test",
            display_name="Stress Test & What-If Scaling",
            status="operational",
            active_sessions=stress_count,
            capacity_limit=None,
        ),
        "arch_defense": SimulationModeStatus(
            mode="arch_defense",
            display_name="Architecture Diagram Defense",
            status="operational",
            active_sessions=arch_count,
            capacity_limit=None,
        ),
    }

    total_active = sum(m.active_sessions for m in modes.values())

    return SimulationReadinessResponse(
        status="healthy",
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
        supported_modes=list(modes.keys()),
        modes=modes,
        total_active_simulations=total_active,
    )


@router.get("/simulations/telemetry", response_model=StoreTelemetry)
async def get_incident_store_telemetry() -> StoreTelemetry:
    """Returns telemetry metrics for the bounded incident simulation store."""
    return incident_session_store.get_stats()
