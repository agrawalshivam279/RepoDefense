"""In-memory bounded catalog, session locking, capacity control, and FSM helpers."""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.schemas.arch_defense import (
    ArchDefenseEvaluationOutput,
    ArchDefenseSessionState,
    ArchDefenseStage,
    ArchDefenseTopic,
    ArchDefenseTurn,
)
from app.schemas.architecture import ArchitectureReportResponse
from app.schemas.diagram import DiagramResponse

MAX_CACHED_PROJECTS = 100
MAX_CACHED_TOPICS_PER_PROJECT = 50
MAX_ACTIVE_SESSIONS = 500
MAX_ACTIVE_SESSIONS_PER_USER = 10


@dataclass
class CachedTopicRecord:
    """Pairs each synthesized defense topic with the exact diagram and report it came from."""

    topic: ArchDefenseTopic
    diagram: DiagramResponse
    report: ArchitectureReportResponse


@dataclass
class ProjectCatalogEntry:
    """Cached default baseline and per-topic paired records for a single project."""

    fingerprint: str
    report: ArchitectureReportResponse
    diagram: DiagramResponse
    topics: Dict[str, CachedTopicRecord] = field(default_factory=dict)
    unfiltered_ids: List[str] = field(default_factory=list)


arch_topic_catalog: Dict[uuid.UUID, ProjectCatalogEntry] = {}
arch_session_store: Dict[str, Tuple[uuid.UUID, ArchDefenseSessionState]] = {}
session_locks: Dict[str, asyncio.Lock] = {}
project_locks: Dict[uuid.UUID, asyncio.Lock] = {}


def compute_arch_fingerprint(project: object, report: ArchitectureReportResponse) -> str:
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


def store_topics_bounded(
    entry: ProjectCatalogEntry,
    topics: List[ArchDefenseTopic],
    report: ArchitectureReportResponse,
    diagram: DiagramResponse,
    set_unfiltered: bool,
) -> None:
    """Retain paired topic records while keeping per-project topic cache memory bounded."""
    keep_ids = {t.id for t in topics}
    for topic in topics:
        entry.topics[topic.id] = CachedTopicRecord(topic=topic, diagram=diagram, report=report)
    if set_unfiltered:
        entry.report, entry.diagram = report, diagram
        entry.unfiltered_ids = [t.id for t in topics]

    protected = keep_ids | set(entry.unfiltered_ids)
    while len(entry.topics) > MAX_CACHED_TOPICS_PER_PROJECT:
        evict_id = next((tid for tid in entry.topics if tid not in protected), None)
        if evict_id is None:
            evict_id = next((tid for tid in entry.topics if tid not in keep_ids), None)
        if evict_id is None:
            break
        entry.topics.pop(evict_id, None)


def ensure_session_capacity(
    user_id: Optional[uuid.UUID] = None,
    max_sessions: int = MAX_ACTIVE_SESSIONS,
    max_per_user: int = MAX_ACTIVE_SESSIONS_PER_USER,
) -> None:
    """Enforce per-user active cap and expire completed sessions; never evict active sessions."""
    if user_id is not None:
        user_active = sum(
            1 for uid, sess in arch_session_store.values()
            if uid == user_id and sess.stage != ArchDefenseStage.COMPLETED
        )
        if user_active >= max_per_user:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many active defense sessions for this user; complete one first.",
            )
    if len(arch_session_store) < max_sessions:
        return
    completed_ids = [
        sid for sid, (_, sess) in arch_session_store.items()
        if sess.stage == ArchDefenseStage.COMPLETED
    ]
    for sid in completed_ids:
        arch_session_store.pop(sid, None)
        session_locks.pop(sid, None)
        if len(arch_session_store) < max_sessions:
            return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Active defense session capacity reached; complete an existing session first.",
    )


def get_owned_session(session_id: str, user_id: uuid.UUID) -> ArchDefenseSessionState:
    """Fetch a session owned by user_id or raise HTTP 404 (prevents IDOR)."""
    record = arch_session_store.get(session_id)
    if not record or record[0] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return record[1]


def advance_session_fsm(
    session: ArchDefenseSessionState,
    eval_out: ArchDefenseEvaluationOutput,
    candidate_turn: Optional[ArchDefenseTurn] = None,
) -> None:
    """Apply atomic candidate-turn persistence, FSM transition, and multi-turn scoring."""
    session.updated_at = datetime.now(timezone.utc).isoformat()
    if candidate_turn is not None:
        session.turns.append(candidate_turn)
    if (
        session.stage == ArchDefenseStage.TOPIC_ACTIVE
        and eval_out.follow_up_challenge
        and not eval_out.is_terminal
    ):
        session.stage = ArchDefenseStage.TRADEOFF_CHALLENGE
        session.current_turn_index += 1
        session.turns.append(
            ArchDefenseTurn(
                role="interviewer",
                stage=ArchDefenseStage.TRADEOFF_CHALLENGE,
                content=(
                    f"Architectural Assessment: {eval_out.feedback}\n\n"
                    f"Tradeoff Challenge:\n{eval_out.follow_up_challenge}"
                ),
                metadata={
                    "depth_score": eval_out.depth_score,
                    "boundary_coherence_score": eval_out.boundary_coherence_score,
                    "pattern_rationale_solid": eval_out.pattern_rationale_solid,
                    "tradeoffs_articulated": eval_out.tradeoffs_articulated,
                },
            )
        )
        return

    prior_evals = [
        t.metadata for t in session.turns
        if t.role == "interviewer"
        and "depth_score" in t.metadata
        and "boundary_coherence_score" in t.metadata
    ]
    all_depths = [int(m["depth_score"]) for m in prior_evals] + [eval_out.depth_score]
    all_bounds = [int(m["boundary_coherence_score"]) for m in prior_evals] + [
        eval_out.boundary_coherence_score
    ]
    turn_avgs = [(d + b) / 2.0 for d, b in zip(all_depths, all_bounds)]

    session.stage = ArchDefenseStage.COMPLETED
    session.overall_score = round(sum(turn_avgs) / len(turn_avgs), 1)
    session.boundary_coherence_score = round(sum(all_bounds) / len(all_bounds))
    if prior_evals:
        first_solid = bool(prior_evals[0].get("pattern_rationale_solid", False))
        second_engaged = bool(eval_out.pattern_rationale_solid or eval_out.tradeoffs_articulated)
        session.pattern_rationale_solid = first_solid and second_engaged
    else:
        session.pattern_rationale_solid = eval_out.pattern_rationale_solid
    session.feedback = eval_out.feedback
    session.turns.append(
        ArchDefenseTurn(
            role="system",
            stage=ArchDefenseStage.COMPLETED,
            content=(
                f"Architecture Defense Concluded. Score: {session.overall_score}/10.\n"
                f"Feedback: {eval_out.feedback}"
            ),
            metadata={
                "overall_score": session.overall_score,
                "turn_scores": [round(s, 1) for s in turn_avgs],
                "depth_score": eval_out.depth_score,
                "boundary_coherence_score": session.boundary_coherence_score,
                "pattern_rationale_solid": session.pattern_rationale_solid,
                "tradeoffs_articulated": eval_out.tradeoffs_articulated,
            },
        )
    )
