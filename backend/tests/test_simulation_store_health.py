"""Hermetic unit and integration tests for Step 3.8a: Simulation Store Hardening & Readiness API."""

import time
import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.ai.fsm import defense_store
from app.api.v1.incident_simulation import incident_session_store
from app.main import app
from app.schemas.health import SimulationReadinessResponse, StoreTelemetry
from app.schemas.incident import (
    ChaosTarget,
    FailureCategory,
    IncidentDefenseSessionState,
    IncidentScenario,
    IncidentSeverity,
    IncidentStage,
)
from app.services.simulation_store import SimulationSessionStore


class TestSimulationSessionStore:
    """Tests for the bounded, thread-safe SimulationSessionStore with LRU and TTL eviction."""

    def test_basic_crud_operations(self):
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=10, ttl_seconds=60.0)
        session_id = uuid.uuid4()

        assert len(store) == 0
        assert session_id not in store

        store.set(session_id, "active_state")
        assert len(store) == 1
        assert session_id in store
        assert store.get(session_id) == "active_state"
        assert store[session_id] == "active_state"

        # Key normalization between UUID and str
        assert store.get(str(session_id)) == "active_state"

        # Update existing key
        store[session_id] = "updated_state"
        assert store[session_id] == "updated_state"
        assert len(store) == 1

        # Delete key
        assert store.delete(session_id) is True
        assert store.delete(session_id) is False
        assert session_id not in store
        assert len(store) == 0

    def test_lru_capacity_eviction(self):
        store: SimulationSessionStore[int] = SimulationSessionStore(max_items=3, ttl_seconds=60.0)
        k1, k2, k3, k4 = "sess-1", "sess-2", "sess-3", "sess-4"

        store.set(k1, 100)
        store.set(k2, 200)
        store.set(k3, 300)
        assert len(store) == 3

        # Access k1 to make it most recently used (LRU order becomes: k2, k3, k1)
        assert store.get(k1) == 100

        # Adding k4 should evict k2 (least recently used)
        store.set(k4, 400)
        assert len(store) == 3
        assert k2 not in store
        assert k1 in store
        assert k3 in store
        assert k4 in store

        stats = store.get_stats()
        assert stats.total_created == 4
        assert stats.total_evicted == 1
        assert stats.active_sessions == 3
        assert stats.max_capacity == 3

    def test_expired_pruned_before_lru_eviction(self):
        """Ensures expired items are pruned before evicting a live LRU item upon saturation."""
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=2, ttl_seconds=60.0)
        store.set("a", "expiring_val", ttl_seconds=0.03)
        store.set("b", "live_val", ttl_seconds=60.0)

        # Access "a" so "b" would be LRU if expiry wasn't checked
        store.get("a")

        # Let "a" expire
        time.sleep(0.05)

        # Inserting "c" should prune expired "a" instead of evicting live "b"
        store.set("c", "new_val")
        assert len(store) == 2
        assert "a" not in store
        assert "b" in store
        assert "c" in store
        assert store.get_stats().total_evicted == 0
        assert store.get_stats().total_expired >= 1

    def test_explicit_ttl_override_when_default_ttl_zero(self):
        """Ensures explicit ttl_seconds override is honored when default store TTL is 0."""
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=5, ttl_seconds=0.0)
        store.set("permanent", "stays", ttl_seconds=0.0)
        store.set("temporary", "expires", ttl_seconds=0.04)

        assert store.get("temporary") == "expires"
        time.sleep(0.05)

        assert store.get("temporary") is None
        assert store.get("permanent") == "stays"

    def test_ttl_expiration_and_pruning(self):
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=5, ttl_seconds=0.05)
        k1 = "expiring-session"

        store.set(k1, "short_lived")
        assert store.get(k1) == "short_lived"

        time.sleep(0.07)

        # Accessing expired key returns default and prunes it
        assert store.get(k1) is None
        assert k1 not in store
        assert len(store) == 0

        stats = store.get_stats()
        assert stats.total_expired >= 1

    def test_prune_expired_batch(self):
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=10, ttl_seconds=0.05)
        store.set("a", "val_a")
        store.set("b", "val_b")
        store.set("c", "val_c", ttl_seconds=10.0)

        time.sleep(0.07)
        pruned_count = store.prune_expired()
        assert pruned_count == 2
        assert len(store) == 1
        assert store.get("c") == "val_c"

    def test_dictionary_iteration_and_helpers(self):
        store: SimulationSessionStore[str] = SimulationSessionStore(max_items=5, ttl_seconds=60.0)
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        store[u1] = "alpha"
        store[u2] = "beta"

        assert set(store.values()) == {"alpha", "beta"}
        assert set(store.keys()) == {u1, u2}
        assert dict(store.items()) == {u1: "alpha", u2: "beta"}

        store.clear()
        assert len(store) == 0
        assert store.values() == []


class TestIncidentStoreIntegration:
    """Verifies incident_simulation router integration with SimulationSessionStore."""

    def test_incident_session_store_is_bounded(self, monkeypatch):
        assert isinstance(incident_session_store, SimulationSessionStore)
        assert incident_session_store._max_items == 100

        isolated_store = SimulationSessionStore[IncidentDefenseSessionState](
            max_items=100, ttl_seconds=86400.0
        )
        monkeypatch.setattr(
            "app.api.v1.incident_simulation.incident_session_store", isolated_store
        )

        sess_id = uuid.uuid4()
        scenario = IncidentScenario(
            title="Redis Exhaustion",
            category=FailureCategory.RESOURCE_EXHAUSTION,
            severity=IncidentSeverity.P1_HIGH,
            hypothetical_trigger="Leaked connections",
            symptoms=["Redis OOM"],
            grounded_target=ChaosTarget(
                file_path="cache.py", symbol_name="get_redis", component_type="queue"
            ),
            incident_question="How would you fix Redis connection pooling?",
            evaluation_criteria=["Max connections", "Connection pool recycling"],
        )
        state = IncidentDefenseSessionState(
            session_id=sess_id,
            project_id=uuid.uuid4(),
            scenario=scenario,
            stage=IncidentStage.TRIAGE,
            turns=[],
            telemetry_snapshot={"cpu_percent": 95},
        )

        isolated_store.set(sess_id, state)
        assert sess_id in isolated_store
        assert isolated_store.get(sess_id) == state


class TestSimulationHealthEndpoints:
    """Verifies the /api/v1/health/simulations diagnostic endpoints."""

    def test_get_simulation_readiness_and_discriminators(self, monkeypatch):
        mock_core = MagicMock()
        mock_core.pr_number = None
        mock_core.commit_hash = None

        mock_pr = MagicMock()
        mock_pr.pr_number = 42
        mock_pr.commit_hash = None

        mock_commit = MagicMock()
        mock_commit.pr_number = None
        mock_commit.commit_hash = "abc1234"

        mock_sessions = {
            "core-1": mock_core,
            "pr-1": mock_pr,
            "commit-1": mock_commit,
        }
        monkeypatch.setattr(defense_store, "_sessions", mock_sessions)

        client = TestClient(app)
        response = client.get("/api/v1/health/simulations")
        assert response.status_code == 200

        data = response.json()
        validated = SimulationReadinessResponse(**data)

        assert validated.status == "healthy"
        assert len(validated.supported_modes) == 6
        expected_modes = {
            "core_defense",
            "pr_defense",
            "commit_defense",
            "incident_simulation",
            "stress_test",
            "arch_defense",
        }
        assert set(validated.supported_modes) == expected_modes

        assert validated.modes["core_defense"].active_sessions == 1
        assert validated.modes["pr_defense"].active_sessions == 1
        assert validated.modes["commit_defense"].active_sessions == 1

    def test_get_simulation_telemetry(self):
        client = TestClient(app)
        response = client.get("/api/v1/health/simulations/telemetry")
        assert response.status_code == 200

        data = response.json()
        validated = StoreTelemetry(**data)
        assert validated.max_capacity == 100
        assert validated.active_sessions >= 0
        assert validated.total_created >= 0
