# 📄 Technical Specification: Step 3.8a — Backend Cross-Simulation Session Store Hardening & Readiness API

> **Step ID**: `Step 3.8a`  
> **Milestone**: `Milestone 3.8: Phase 3 Polish & Deploy`  
> **Target Module**: `backend/app/services/simulation_store.py`, `backend/app/api/v1/incident_simulation.py`, `backend/app/api/v1/health.py`, `backend/app/main.py`  
> **Git Feature Branch**: `feat/step-3-8a-simulation-store-health`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-11-13  

---

## 1. Executive Summary

Throughout **Phase 3: Advanced Defense** (Milestones 3.1 through 3.7), RepoDefense expanded from its Phase 1 single-turn oral defense into a multi-simulation defense platform featuring 5 specialized engines:
1. **PR Defense** (`/api/v1/pr-defense` — diff parsing & change defense)
2. **Commit Defense** (`/api/v1/commit-defense` — commit diff parsing & scoped defense)
3. **Incident Simulation War Room** (`/api/v1/incident-simulation` — SRE chaos failure triage & mitigation)
4. **Stress Test / What-If Mode** (`/api/v1/stress-test` — high-concurrency scaling escalation)
5. **Architecture Defense Mode** (`/api/v1/arch-defense` — diagram-grounded topology & tradeoff interrogation)
6. **Cross-Mode Analytics Engine** (`/api/v1/analytics` — radar metrics & readiness trend)

While `stress_cache.py` and `arch_defense_store.py` established bounded caching for scaling scenarios and architecture topics, `incident_simulation.py` still relies on an unbounded raw in-memory dictionary (`incident_session_store: Dict[uuid.UUID, IncidentDefenseSessionState] = {}`) without memory caps, TTL expiration, or eviction metrics. In addition, RepoDefense lacks a centralized operational health and readiness diagnostic endpoint reporting active session metrics across all Phase 3 defense modes before production deployment.

**Step 3.8a** delivers the backend polish for Milestone 3.8:
- Authors a generic, thread/async-safe `SimulationSessionStore[T]` in `backend/app/services/simulation_store.py` featuring bounded capacity (`max_items`), configurable TTL eviction (e.g., 24h), LRU eviction upon saturation, and observable telemetry counters.
- Refactors `backend/app/api/v1/incident_simulation.py` to use `SimulationSessionStore`, removing the unbounded global dictionary while preserving all existing route contracts and tenant IDOR protections.
- Authors a dedicated simulation readiness router in `backend/app/api/v1/health.py` exposing `GET /api/v1/health/simulations`, reporting service readiness, registered simulation modes, active session telemetry, and memory capacity limits across all defense engines.
- Mounts the health router in `backend/app/main.py` and authors hermetic unit and endpoint tests in `backend/tests/test_simulation_store_health.py`.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Step 3.4a`: Backend Incident Simulation Engine (`backend/app/api/v1/incident_simulation.py`)
  - `Step 3.5a`: Backend Stress Test Engine (`backend/app/api/v1/stress_test.py`)
  - `Step 3.6a`: Backend Architecture Defense Engine (`backend/app/api/v1/arch_defense.py`)
  - `Step 3.7a`: Backend Performance Analytics Service (`backend/app/api/v1/analytics.py`)
- **Blocked by**: None.
- **Tech Stack Invariants**:
  - Python 3.12+ / FastAPI / Pydantic v2
  - Strict $\le 300$ LOC per file limit (Gemini.md invariant)
  - Zero arbitrary code execution

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Operates purely on memory data structures and HTTP health diagnostics; no `eval()`, `exec()`, or subshell execution.
- [x] **DoS & Memory Exhaustion Prevention**: Hard bounds (`max_items=100`) and automatic LRU eviction prevent memory exhaustion from abandoned or high-volume interview sessions.
- [x] **Tenant IDOR Enforcement**: Preserves strict `Project.user_id == current_user.id` validation on session retrieval and turn progression.
- [x] **Safe Observable Telemetry**: Diagnostics expose aggregate session counts, operational states, and capacities with zero PII or user code leakages.
- [x] **File Length Gate**: All modified and new files strictly adhere to the $\le 300$ LOC limit.

---

## 4. 🩺 Specialized Domain Skill Advisory

### `doctor` Pre-Flight & Health Directive
- Audit environment readiness and health diagnostics.
- Ensure the new `/api/v1/health/simulations` endpoint provides transparent operational status for automated health probes and CI/CD smoke tests without disrupting the root `/api/health` probe.

---

## 5. Data Contracts & Interfaces

### 5.1 Store Telemetry & Readiness Schemas (`backend/app/schemas/health.py`)

```python
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StoreTelemetry(BaseModel):
    """Telemetry metrics for an in-memory simulation session store."""
    active_sessions: int = Field(..., description="Currently active sessions in memory")
    max_capacity: int = Field(..., description="Maximum allowed sessions before LRU eviction")
    total_created: int = Field(default=0, description="Cumulative sessions created since boot")
    total_evicted: int = Field(default=0, description="Cumulative sessions evicted via LRU")
    total_expired: int = Field(default=0, description="Cumulative sessions pruned via TTL")


class SimulationModeStatus(BaseModel):
    """Operational status and metrics for an individual simulation mode."""
    mode: str = Field(..., description="Mode identifier (e.g., incident_simulation, stress_test)")
    display_name: str = Field(..., description="Human-readable mode title")
    status: str = Field(default="operational", description="operational | degraded | offline")
    active_sessions: int = Field(default=0, description="Number of currently active sessions")
    capacity_limit: Optional[int] = Field(default=None, description="Max session capacity if bounded")


class SimulationReadinessResponse(BaseModel):
    """Aggregated health and readiness report across all defense simulation engines."""
    status: str = Field(default="healthy", description="healthy | degraded")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version string")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC server timestamp",
    )
    supported_modes: List[str] = Field(..., description="List of all supported defense modes")
    modes: Dict[str, SimulationModeStatus] = Field(
        ..., description="Per-mode operational status and session counts"
    )
    total_active_simulations: int = Field(
        ..., description="Sum of active sessions across all simulation stores"
    )
```

---

## 6. Target Files & LOC Budget

| File | Status | Target LOC | Role |
| :--- | :--- | :--- | :--- |
| `backend/app/services/simulation_store.py` | `[NEW]` | ~170 LOC | Bounded generic LRU/TTL session store with thread/coroutine safety and telemetry. |
| `backend/app/api/v1/incident_simulation.py` | `[MODIFY]` | ~255 LOC | Refactor to use `SimulationSessionStore`, removing unbounded dictionary. |
| `backend/app/api/v1/health.py` | `[NEW]` | ~130 LOC | Simulation readiness router exposing `GET /api/v1/health/simulations`. |
| `backend/app/main.py` | `[MODIFY]` | ~95 LOC | Mount health router under `/api/v1/health`. |
| `backend/tests/test_simulation_store_health.py` | `[NEW]` | ~220 LOC | Unit & endpoint integration tests for bounded store and readiness API. |

*Total files*: 5 files ($\le 4$ implementation/test files + 1 2-line router mount in `main.py`).  
*Max file size*: $\le 255$ LOC (strictly within 300 LOC limit).

---

## 7. Step-by-Step Implementation Sequence

1. **Phase A: Bounded Generic Session Store (`backend/app/services/simulation_store.py`)**
   - Implement `SimulationSessionStore[T]` with:
     - `max_items: int = 100` (configurable capacity limit)
     - `ttl_seconds: int = 86400` (24-hour default TTL)
     - `OrderedDict` backing store for $O(1)$ LRU eviction on saturation
     - Thread/asyncio lock synchronization for atomic mutations
     - Methods: `get(session_id)`, `set(session_id, item)`, `delete(session_id)`, `clear()`, `get_stats() -> StoreTelemetry`, `prune_expired() -> int`

2. **Phase B: Refactor Incident Simulation Router (`backend/app/api/v1/incident_simulation.py`)**
   - Replace `incident_session_store: Dict[...] = {}` with a module-level `incident_session_store = SimulationSessionStore[IncidentDefenseSessionState](max_items=100, ttl_seconds=86400)`.
   - Update `start_incident_defense_endpoint`, `get_incident_session_endpoint`, and `respond_to_incident_turn_endpoint` to use `incident_session_store.set` and `incident_session_store.get`.
   - Maintain 100% backward compatibility for all existing tests and responses.

3. **Phase C: Simulation Readiness API & Mounting (`backend/app/api/v1/health.py` & `backend/app/main.py`)**
   - Create router with `GET /simulations` endpoint (prefixed with `/api/v1/health`).
   - Query session counts from:
     - `defense_store` (Oral Defense)
     - `pr_defense_store` / `defense_store` (PR Defense)
     - `commit_defense_store` / `defense_store` (Commit Defense)
     - `incident_session_store` (Incident Simulation)
     - `stress_defense_store` in `stress_test.py` (Stress Test)
     - `arch_session_store` in `arch_defense_store.py` (Architecture Defense)
   - Assemble `SimulationReadinessResponse` with `healthy` status and mode counts.
   - Mount router in `backend/app/main.py`.

4. **Phase D: Hermetic Test Suite (`backend/tests/test_simulation_store_health.py`)**
   - Test store capacity enforcement (101 items in a max-100 store evicts the oldest LRU item).
   - Test TTL pruning (expired items return None and increment `total_expired`).
   - Test store telemetry (`active_sessions`, `total_created`, `total_evicted`).
   - Test incident simulation endpoints work seamlessly with the bounded store.
   - Test `GET /api/v1/health/simulations` returns 200 with all 6 modes listed and correct total active count.

---

## 8. Verification & Acceptance Criteria

### Automated Tests
```bash
python -m pytest backend/tests/test_simulation_store_health.py -v
```

### Acceptance Checklist
- [ ] `SimulationSessionStore` enforces `max_items` and LRU eviction order.
- [ ] `SimulationSessionStore` prunes items older than `ttl_seconds`.
- [ ] `incident_session_store` in `incident_simulation.py` is fully bounded with zero unbounded memory growth.
- [ ] `GET /api/v1/health/simulations` returns HTTP 200 with valid `SimulationReadinessResponse` schema.
- [ ] All 307 existing tests pass with zero regressions.
- [ ] `python -m ruff check backend/app backend/tests` returns zero errors.
- [ ] All touched files strictly conform to the $\le 300$ LOC limit.
