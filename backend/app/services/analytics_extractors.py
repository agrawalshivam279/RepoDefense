"""Normalize defense session state records from heterogeneous mode stores."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.ai.fsm import DefenseSessionStore, defense_store
from app.schemas.analytics import DefenseModeKey
from app.schemas.arch_defense import ArchDefenseStage
from app.schemas.commit_defense import CommitDefenseSessionState
from app.schemas.defense import DefenseStage
from app.schemas.incident import IncidentStage
from app.schemas.pr_defense import PRDefenseSessionState
from app.schemas.stress_test import StressSessionStage
from app.services.arch_defense_store import arch_session_store
from app.services.stress_cache import stress_session_store

MODE_LABELS: Dict[DefenseModeKey, str] = {
    DefenseModeKey.CORE_DEFENSE: "Core Defense",
    DefenseModeKey.PR_DEFENSE: "PR Defense",
    DefenseModeKey.COMMIT_DEFENSE: "Commit Defense",
    DefenseModeKey.STRESS_TEST: "Stress Test",
    DefenseModeKey.INCIDENT_SIMULATION: "Incident War Room",
    DefenseModeKey.ARCH_DEFENSE: "Architecture Defense",
}


@dataclass
class SessionSample:
    """Normalized defense session datapoint across heterogeneous stores."""

    session_id: str
    project_id: str
    mode: DefenseModeKey
    completed: bool
    score_pct: Optional[float]
    timestamp: str
    topic_or_title: str
    skills: Dict[str, float] = field(default_factory=dict)


def normalize_score(raw: Optional[float], scale_10: bool) -> Optional[float]:
    """Converts a raw mode score into a clamped 0.0-100.0 percentage."""
    if raw is None:
        return None
    val = float(raw) * 10.0 if scale_10 else float(raw)
    return round(max(0.0, min(100.0, val)), 1)


def _extract_core_family_sample(session: Any) -> SessionSample:
    if isinstance(session, PRDefenseSessionState):
        mode = DefenseModeKey.PR_DEFENSE
        title = f"PR #{session.pr_number}: {session.pr_title}"
    elif isinstance(session, CommitDefenseSessionState):
        mode = DefenseModeKey.COMMIT_DEFENSE
        title = f"Commit {session.commit_hash[:7]}: {session.commit_message}"
    else:
        mode = DefenseModeKey.CORE_DEFENSE
        q_list = getattr(session, "questions", None) or []
        first_q = (
            q_list[0].question.question_text
            if q_list and getattr(q_list[0], "question", None)
            else ""
        )
        fallback_title = first_q or "Core Codebase Defense"
        title = (first_q[:57] + "...") if len(first_q) > 60 else fallback_title

    skills = {
        str(k): round(max(0.0, min(100.0, float(v) * 100.0)), 1)
        for k, v in (session.topic_confidence or {}).items()
    }
    return SessionSample(
        session_id=str(session.session_id),
        project_id=str(session.project_id),
        mode=mode,
        completed=session.status == DefenseStage.SESSION_COMPLETED,
        score_pct=normalize_score(session.overall_score, scale_10=True),
        timestamp=str(session.updated_at or session.created_at),
        topic_or_title=title,
        skills=skills,
    )


def _extract_stress_sample(session: Any) -> SessionSample:
    score_pct = normalize_score(session.overall_score, scale_10=True)
    skills: Dict[str, float] = {}
    if score_pct is not None and getattr(session, "scenario", None):
        skills[f"stress:{session.scenario.constraint_type.value}"] = score_pct
    return SessionSample(
        session_id=str(session.session_id),
        project_id=str(session.project_id),
        mode=DefenseModeKey.STRESS_TEST,
        completed=session.stage == StressSessionStage.COMPLETED,
        score_pct=score_pct,
        timestamp=str(session.updated_at or session.created_at),
        topic_or_title=getattr(session.scenario, "title", "Scaling Stress Scenario"),
        skills=skills,
    )


def _extract_incident_sample(session: Any) -> SessionSample:
    score_pct = normalize_score(session.overall_score, scale_10=False)
    skills: Dict[str, float] = {}
    if score_pct is not None and getattr(session, "scenario", None):
        skills[f"incident:{session.scenario.category.value}"] = score_pct
    ts = (
        getattr(session, "updated_at", None)
        or getattr(session, "created_at", None)
        or datetime.now(timezone.utc).isoformat()
    )
    return SessionSample(
        session_id=str(session.id),
        project_id=str(session.project_id),
        mode=DefenseModeKey.INCIDENT_SIMULATION,
        completed=session.stage == IncidentStage.POSTMORTEM,
        score_pct=score_pct,
        timestamp=str(ts),
        topic_or_title=getattr(session.scenario, "title", "Incident Simulation"),
        skills=skills,
    )


def _extract_arch_sample(session: Any) -> SessionSample:
    score_pct = normalize_score(session.overall_score, scale_10=True)
    skills: Dict[str, float] = {}
    if score_pct is not None and getattr(session, "topic", None):
        skills[f"arch:{session.topic.focus_area.value.lower()}"] = score_pct
    coherence = normalize_score(getattr(session, "boundary_coherence_score", None), scale_10=True)
    if coherence is not None:
        skills["boundary_coherence"] = coherence
    return SessionSample(
        session_id=str(session.session_id),
        project_id=str(session.project_id),
        mode=DefenseModeKey.ARCH_DEFENSE,
        completed=session.stage == ArchDefenseStage.COMPLETED,
        score_pct=score_pct,
        timestamp=str(session.updated_at or session.created_at),
        topic_or_title=getattr(session.topic, "title", "Architecture Defense"),
        skills=skills,
    )


async def collect_samples_for_projects(
    allowed_project_ids: Set[str],
    fsm_store: Optional[DefenseSessionStore] = None,
    stress_store: Optional[Dict[str, Any]] = None,
    incident_store: Optional[Dict[Any, Any]] = None,
    arch_store: Optional[Dict[str, Any]] = None,
) -> List[SessionSample]:
    """Collects normalized defense session samples strictly filtered by allowed_project_ids."""
    if not allowed_project_ids:
        return []

    target_fsm = fsm_store if fsm_store is not None else defense_store
    target_stress = stress_store if stress_store is not None else stress_session_store
    target_arch = arch_store if arch_store is not None else arch_session_store
    if incident_store is None:
        from app.api.v1.incident_simulation import incident_session_store

        target_incident: Dict[Any, Any] = incident_session_store
    else:
        target_incident = incident_store

    samples: List[SessionSample] = []
    for pid in allowed_project_ids:
        for sess in await target_fsm.get_by_project(pid):
            samples.append(_extract_core_family_sample(sess))

    extractors: Sequence[Tuple[Iterable[Any], Any]] = (
        (target_stress.values(), _extract_stress_sample),
        (target_incident.values(), _extract_incident_sample),
        (target_arch.values(), _extract_arch_sample),
    )
    for iterable, fn in extractors:
        for sess in iterable:
            if str(getattr(sess, "project_id", "")) in allowed_project_ids:
                samples.append(fn(sess))
    return samples
