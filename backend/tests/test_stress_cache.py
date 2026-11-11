"""Hermetic tests for bounded stress scenario caching and view isolation."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.stress_test_generator import build_deterministic_stress_scenarios
from app.api.v1.stress_test import (
    get_or_generate_stress_scenarios,
    project_stress_cache,
    start_stress_defense_session,
)
from app.models.analysis import Dependency, Evidence
from app.models.project import Project, User
from app.schemas.stress_test import (
    GenerateStressScenariosRequest,
    StartStressDefenseRequest,
    StressConstraintType,
)
from app.services.stress_cache import (
    MAX_CACHED_SCENARIOS_PER_PROJECT,
    _unfiltered_catalog_meta,
    cache_project_scenarios,
    clear_all_stress_state,
    compute_evidence_version,
    get_cached_unfiltered_scenarios,
    restore_stress_state,
    snapshot_stress_state,
)
from tests.test_stress_test import _drive_coro


class TestStressScenarioCacheIsolation:
    """Validates filtered preservation, eviction safety, stale view & evidence guards."""

    def setup_method(self):
        self._saved_state = snapshot_stress_state()
        clear_all_stress_state()
        self.user_id = uuid.uuid4()
        self.user = User(id=self.user_id, email="cache@repodefense.dev")
        self.project_id = uuid.uuid4()
        self.project = Project(id=self.project_id, user_id=self.user_id, name="CacheRepo")

    def teardown_method(self):
        restore_stress_state(self._saved_state)

    def _mock_db(self, evidence_batches=None, dependency_batches=None):
        db = AsyncMock()
        ev_batches = list(evidence_batches) if evidence_batches is not None else [[]]
        dep_batches = list(dependency_batches) if dependency_batches is not None else [[]]

        def _execute(stmt):
            res = MagicMock()
            res.scalar_one_or_none.return_value = self.project
            scalars_mock = MagicMock()
            entity = stmt.column_descriptions[0].get("entity")
            if entity is Evidence:
                next_batch = ev_batches.pop(0) if len(ev_batches) > 1 else ev_batches[0]
            elif entity is Dependency:
                next_batch = dep_batches.pop(0) if len(dep_batches) > 1 else dep_batches[0]
            else:
                next_batch = []
            scalars_mock.all.return_value = next_batch
            res.scalars.return_value = scalars_mock
            return res

        db.execute = AsyncMock(side_effect=_execute)
        return db

    def test_start_session_preserves_filtered_scenario(self):
        db = self._mock_db()
        filtered_req = GenerateStressScenariosRequest(
            constraint_type=StressConstraintType.DB_CONNECTION_STARVATION,
            max_scenarios=2,
            api_key="",
        )
        filtered_resp = _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id, filtered_req, current_user=self.user, db=db
            )
        )
        assert filtered_resp.total_scenarios >= 1
        target_id = filtered_resp.scenarios[0].id

        unfiltered_resp = _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id,
                GenerateStressScenariosRequest(api_key=""),
                current_user=self.user,
                db=db,
            )
        )
        assert unfiltered_resp.total_scenarios >= 2

        session = _drive_coro(
            start_stress_defense_session(
                self.project_id,
                StartStressDefenseRequest(scenario_id=target_id),
                current_user=self.user,
                db=db,
            )
        )
        assert session.scenario.id == target_id
        assert session.scenario.constraint_type == StressConstraintType.DB_CONNECTION_STARVATION

    def test_start_session_unknown_scenario_returns_404(self):
        db = self._mock_db()
        _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id,
                GenerateStressScenariosRequest(api_key=""),
                current_user=self.user,
                db=db,
            )
        )
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(
                start_stress_defense_session(
                    self.project_id,
                    StartStressDefenseRequest(scenario_id="unknown-scenario-999"),
                    current_user=self.user,
                    db=db,
                )
            )
        assert exc_info.value.status_code == 404

    def test_project_scenario_cache_is_bounded(self):
        base = build_deterministic_stress_scenarios("CacheRepo")[0]
        extra = MAX_CACHED_SCENARIOS_PER_PROJECT + 5
        for idx in range(extra):
            clone = base.model_copy(update={"id": f"stress-extra-{idx}"})
            cache_project_scenarios(
                self.project_id, [clone], is_unfiltered=False, requested_limit=1
            )
        cached = project_stress_cache[self.project_id]
        assert len(cached) == MAX_CACHED_SCENARIOS_PER_PROJECT
        assert cached[-1].id == f"stress-extra-{extra - 1}"
        assert cached[0].id == "stress-extra-5"

    def test_stale_view_request_cannot_evict_active_view(self):
        db = self._mock_db()
        active_req = GenerateStressScenariosRequest(
            constraint_type=StressConstraintType.MEMORY_PRESSURE,
            max_scenarios=2,
            api_key="",
            view_id="tab-1",
            request_seq=2,
        )
        active_resp = _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id, active_req, current_user=self.user, db=db
            )
        )
        active_ids = {s.id for s in active_resp.scenarios}
        stale_req = GenerateStressScenariosRequest(
            constraint_type=StressConstraintType.CONCURRENCY_SPIKE,
            max_scenarios=3,
            api_key="",
            view_id="tab-1",
            request_seq=1,
        )
        _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id, stale_req, current_user=self.user, db=db
            )
        )
        cached_ids = {s.id for s in project_stress_cache[self.project_id]}
        assert active_ids.issubset(cached_ids)

        base = build_deterministic_stress_scenarios("CacheRepo")[0]
        extras = [
            base.model_copy(update={"id": f"filler-{i}"})
            for i in range(MAX_CACHED_SCENARIOS_PER_PROJECT)
        ]
        cache_project_scenarios(self.project_id, extras, is_unfiltered=False, requested_limit=1)
        final_ids = {s.id for s in project_stress_cache[self.project_id]}
        assert active_ids.issubset(final_ids)
        assert len(project_stress_cache[self.project_id]) == MAX_CACHED_SCENARIOS_PER_PROJECT

    def test_unfiltered_cache_misses_when_unfiltered_ids_evicted(self):
        base = build_deterministic_stress_scenarios("CacheRepo")[0]
        ver = compute_evidence_version(self.project, [])
        unfiltered = [base.model_copy(update={"id": f"unfilt-{i}"}) for i in range(4)]
        cache_project_scenarios(
            self.project_id,
            unfiltered,
            is_unfiltered=True,
            requested_limit=4,
            evidence_version=ver,
        )
        project_stress_cache[self.project_id] = unfiltered[:2]
        assert get_cached_unfiltered_scenarios(self.project_id, 4, evidence_version=ver) is None
        assert self.project_id not in _unfiltered_catalog_meta

    def test_unfiltered_cache_invalidates_when_evidence_changes(self):
        ev_new = SimpleNamespace(
            id=uuid.uuid4(),
            file_path="app/db.py",
            title="get_pool",
            evidence_type="database",
        )
        # Call 1 (initial + post-recheck = []); Call 2 ([ev_new]) -> invalidates cache
        db = self._mock_db(evidence_batches=[[], [], [ev_new]])
        _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id,
                GenerateStressScenariosRequest(max_scenarios=2, api_key=""),
                current_user=self.user,
                db=db,
            )
        )
        resp2 = _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id,
                GenerateStressScenariosRequest(max_scenarios=2, api_key=""),
                current_user=self.user,
                db=db,
            )
        )
        assert str(ev_new.id) in resp2.scenarios[0].cited_evidence_ids

    def test_inflight_generation_does_not_cache_stale_evidence_catalog(self):
        ev_late = SimpleNamespace(
            id=uuid.uuid4(),
            file_path="app/cache.py",
            title="redis_client",
            evidence_type="cache",
        )
        batches = [[], [ev_late]]
        db = self._mock_db(evidence_batches=batches)
        seen_evidence_counts = []

        async def _fake_gen(**kwargs):
            seen_evidence_counts.append(len(kwargs["evidence_items"]))
            return build_deterministic_stress_scenarios(
                kwargs["project_name"], kwargs["evidence_items"], max_scenarios=2
            )

        with patch("app.api.v1.stress_test.generate_stress_scenarios", side_effect=_fake_gen):
            resp = _drive_coro(
                get_or_generate_stress_scenarios(
                    self.project_id,
                    GenerateStressScenariosRequest(max_scenarios=2, api_key=""),
                    current_user=self.user,
                    db=db,
                )
            )
        assert seen_evidence_counts == [0, 1]
        assert str(ev_late.id) in resp.scenarios[0].cited_evidence_ids
