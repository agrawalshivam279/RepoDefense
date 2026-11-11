"""Bounded in-memory cache and active-view sequence tracking for Stress Test Mode."""

import hashlib
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.stress_test import StressDefenseSessionState, StressTestScenario

stress_session_store: Dict[str, StressDefenseSessionState] = {}
project_stress_cache: Dict[uuid.UUID, List[StressTestScenario]] = {}
_unfiltered_catalog_meta: Dict[uuid.UUID, Tuple[int, Set[str], str]] = {}
_active_view_state: Dict[Tuple[uuid.UUID, str], Tuple[int, Set[str]]] = {}

MAX_CACHED_SCENARIOS_PER_PROJECT = 25
MAX_ACTIVE_VIEWS_PER_PROJECT = 10


def compute_evidence_version(project: Any, evidence_items: List[dict]) -> str:
    """Compute a deterministic fingerprint of project analysis status and committed evidence."""
    status_val = getattr(project, "status", "")
    status_str = status_val.value if hasattr(status_val, "value") else str(status_val or "")
    updated_val = getattr(project, "updated_at", "")
    updated_str = str(updated_val or "")
    parts = [status_str, updated_str]
    rows = sorted(
        f"{item.get('id', '')}|{item.get('file_path', '')}|"
        f"{item.get('symbol_name', '')}|{item.get('type', '')}"
        for item in evidence_items
    )
    parts.extend(rows)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def snapshot_stress_state() -> Dict[str, Any]:
    """Capture a deep copy of all module-level caches for hermetic test teardown."""
    return {
        "sessions": {k: v.model_copy(deep=True) for k, v in stress_session_store.items()},
        "cache": {k: list(v) for k, v in project_stress_cache.items()},
        "meta": {
            k: (lim, set(ids), ver)
            for k, (lim, ids, ver) in _unfiltered_catalog_meta.items()
        },
        "views": {k: (seq, set(ids)) for k, (seq, ids) in _active_view_state.items()},
    }


def clear_all_stress_state() -> None:
    """Clear all in-memory stress sessions, caches, and active-view tracking state."""
    stress_session_store.clear()
    project_stress_cache.clear()
    _unfiltered_catalog_meta.clear()
    _active_view_state.clear()


def restore_stress_state(snapshot: Dict[str, Any]) -> None:
    """Restore previously captured cache and session state after a test finishes."""
    clear_all_stress_state()
    stress_session_store.update(snapshot["sessions"])
    project_stress_cache.update(snapshot["cache"])
    _unfiltered_catalog_meta.update(snapshot["meta"])
    _active_view_state.update(snapshot["views"])


def clear_project_meta(project_id: uuid.UUID) -> None:
    """Reset auxiliary tracking metadata when a project is absent from the scenario cache."""
    _unfiltered_catalog_meta.pop(project_id, None)
    for key in [k for k in _active_view_state if k[0] == project_id]:
        _active_view_state.pop(key, None)


def record_active_view_seq(
    project_id: uuid.UUID,
    view_id: str,
    request_seq: int,
    scenario_ids: Optional[Set[str]] = None,
) -> bool:
    """Track monotonic sequence per view; return False if superseded by a newer request."""
    view_key = (project_id, view_id)
    prev_seq, prev_ids = _active_view_state.get(view_key, (-1, set()))
    if request_seq < prev_seq:
        return False
    _active_view_state.pop(view_key, None)
    _active_view_state[view_key] = (
        request_seq,
        scenario_ids if scenario_ids is not None else prev_ids,
    )
    project_views = [k for k in _active_view_state if k[0] == project_id]
    while len(project_views) > MAX_ACTIVE_VIEWS_PER_PROJECT:
        _active_view_state.pop(project_views.pop(0), None)
    return True


def invalidate_if_evidence_changed(project_id: uuid.UUID, evidence_version: str) -> None:
    """Invalidate unfiltered catalog metadata when repository evidence changes."""
    meta = _unfiltered_catalog_meta.get(project_id)
    if meta is not None and meta[2] != evidence_version:
        _unfiltered_catalog_meta.pop(project_id, None)


def get_cached_unfiltered_scenarios(
    project_id: uuid.UUID,
    max_scenarios: int,
    *,
    evidence_version: str,
) -> Optional[List[StressTestScenario]]:
    """Return cached unfiltered catalog only if complete and matching current evidence."""
    cached_catalog = project_stress_cache.get(project_id)
    unfiltered_meta = _unfiltered_catalog_meta.get(project_id)
    if cached_catalog is None or unfiltered_meta is None:
        return None
    prev_limit, unfiltered_ids, cached_version = unfiltered_meta
    if cached_version != evidence_version:
        _unfiltered_catalog_meta.pop(project_id, None)
        return None
    matched = [s for s in cached_catalog if s.id in unfiltered_ids]
    if len(matched) != len(unfiltered_ids):
        _unfiltered_catalog_meta.pop(project_id, None)
        return None
    if prev_limit >= max_scenarios or len(matched) >= max_scenarios:
        return matched[:max_scenarios]
    return None


def cache_project_scenarios(
    project_id: uuid.UUID,
    scenarios: List[StressTestScenario],
    *,
    is_unfiltered: bool,
    requested_limit: int,
    evidence_version: str = "",
) -> bool:
    """Merge scenarios into bounded cache; return True if every new scenario stayed retained."""
    existing = {s.id: s for s in project_stress_cache.get(project_id, [])}
    for scenario in scenarios:
        existing.pop(scenario.id, None)
        existing[scenario.id] = scenario

    if is_unfiltered:
        unfiltered_ids = {s.id for s in scenarios}
        _unfiltered_catalog_meta[project_id] = (requested_limit, unfiltered_ids, evidence_version)
    else:
        meta = _unfiltered_catalog_meta.get(project_id)
        unfiltered_ids = meta[1] if meta else set()

    protected_ids = set(unfiltered_ids)
    for (pid, _), (_, view_ids) in _active_view_state.items():
        if pid == project_id:
            protected_ids.update(view_ids)

    evictable = [sid for sid in existing if sid not in protected_ids]
    while len(existing) > MAX_CACHED_SCENARIOS_PER_PROJECT and evictable:
        existing.pop(evictable.pop(0), None)
    while len(existing) > MAX_CACHED_SCENARIOS_PER_PROJECT:
        existing.pop(next(iter(existing)))

    meta = _unfiltered_catalog_meta.get(project_id)
    if meta is not None and not meta[1].issubset(existing.keys()):
        _unfiltered_catalog_meta.pop(project_id, None)

    project_stress_cache[project_id] = list(existing.values())
    return all(s.id in existing for s in scenarios)
