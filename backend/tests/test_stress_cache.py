"""Hermetic tests for bounded stress scenario caching and view isolation."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.ai.stress_test_generator import build_deterministic_stress_scenarios
from app.api.v1.stress_test import (
    get_or_generate_stress_scenarios,
    project_stress_cache,
    start_stress_defense_session,
)
from app.models.project import Project, User
from app.schemas.stress_test import (
    GenerateStressScenariosRequest,
    StartStressDefenseRequest,
    StressConstraintType,
)
from app.services.stress_cache import (
    MAX_CACHED_SCENARIOS_PER_PROJECT,
    cache_project_scenarios,
    clear_all_stress_state,
    restore_stress_state,
    snapshot_stress_state,
)
from tests.test_stress_test import _drive_coro


class TestStressScenarioCacheIsolation:
    """Validates filtered scenario preservation, bounded eviction, and stale view protection."""

    def setup_method(self):
        self._saved_state = snapshot_stress_state()
        clear_all_stress_state()
        self.user_id = uuid.uuid4()
        self.user = User(id=self.user_id, email="cache@repodefense.dev")
        self.project_id = uuid.uuid4()
        self.project = Project(id=self.project_id, user_id=self.user_id, name="CacheRepo")

    def teardown_method(self):
        restore_stress_state(self._saved_state)

    def _mock_db(self):
        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalar_one_or_none.return_value = self.project
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_res.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=exec_res)
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

        # Even when unrelated scenarios fill capacity, active view scenarios stay protected
        base = build_deterministic_stress_scenarios("CacheRepo")[0]
        extras = [
            base.model_copy(update={"id": f"filler-{i}"})
            for i in range(MAX_CACHED_SCENARIOS_PER_PROJECT)
        ]
        cache_project_scenarios(self.project_id, extras, is_unfiltered=False, requested_limit=1)
        final_ids = {s.id for s in project_stress_cache[self.project_id]}
        assert active_ids.issubset(final_ids)
        assert len(project_stress_cache[self.project_id]) == MAX_CACHED_SCENARIOS_PER_PROJECT
