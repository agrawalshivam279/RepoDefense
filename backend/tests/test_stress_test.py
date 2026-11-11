"""Hermetic unit and integration tests for Step 3.5a: Stress Test & What-If Mode."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.ai.stress_test_generator import (
    build_deterministic_stress_evaluation,
    build_deterministic_stress_scenarios,
    evaluate_stress_defense,
    generate_stress_scenarios,
)
from app.api.v1.stress_test import (
    get_or_generate_stress_scenarios,
    get_stress_session,
    project_stress_cache,
    start_stress_defense_session,
    submit_stress_defense_turn,
)
from app.models.project import Project, User
from app.schemas.stress_test import (
    GenerateStressScenariosRequest,
    StartStressDefenseRequest,
    StressConstraintType,
    StressEvaluationOutput,
    StressSessionStage,
    StressSeverity,
    StressTarget,
    StressTestScenario,
    SubmitStressAnswerRequest,
)
from app.services.stress_cache import (
    clear_all_stress_state,
    restore_stress_state,
    snapshot_stress_state,
)


def _drive_coro(coro):
    """Hermetic coroutine runner without event loop dependency."""
    stack, val, exc = [coro], None, None
    while stack:
        current = stack[-1]
        try:
            to_send = current.throw(exc) if exc is not None else current.send(val)
            exc, val = None, None
            if hasattr(to_send, "send"):
                stack.append(to_send)
        except StopIteration as stop:
            val, _ = stop.value, stack.pop()
        except Exception as e:
            exc, _ = e, stack.pop()
    if exc is not None:
        raise exc
    return val


class TestStressSchemas:
    """Tests for Pydantic schemas and serialization."""

    def test_schema_instantiation(self):
        target = StressTarget(
            symbol_name="query_users",
            file_path="app/api/users.py",
            line_range="10-25",
            component_type="endpoint",
        )
        scenario = StressTestScenario(
            title="Concurrency Spike on User Query",
            constraint_type=StressConstraintType.CONCURRENCY_SPIKE,
            severity=StressSeverity.SEVERE,
            target=target,
            context_description="Nominal query",
            hypothetical_prompt="What happens if 20,000 req/sec hit this?",
            expected_tradeoffs=["Connection pool latency", "CPU limits"],
        )
        assert scenario.constraint_type == StressConstraintType.CONCURRENCY_SPIKE
        assert scenario.target.symbol_name == "query_users"

        eval_out = StressEvaluationOutput(
            depth_score=8,
            bottleneck_identified=True,
            scaling_strategy_sound=True,
            tradeoffs_acknowledged=True,
            feedback="Great scaling plan",
            follow_up_constraint="What if cache evicts?",
            is_terminal=False,
        )
        assert eval_out.depth_score == 8
        assert not eval_out.is_terminal


class TestStressGeneratorAndFallbacks:
    """Tests for deterministic scaling scenario generation and evaluation."""

    def test_build_deterministic_scenarios(self):
        evidence = [{"file_path": "backend/app/main.py", "symbol_name": "app", "id": "ev-1"}]
        scenarios = build_deterministic_stress_scenarios(
            project_name="RepoDefense",
            evidence_items=evidence,
            constraint_type=StressConstraintType.CONCURRENCY_SPIKE,
            max_scenarios=2,
        )
        assert len(scenarios) == 1
        assert scenarios[0].constraint_type == StressConstraintType.CONCURRENCY_SPIKE
        assert "ev-1" in scenarios[0].cited_evidence_ids

    def test_build_deterministic_evaluation_strong(self):
        scenario = build_deterministic_stress_scenarios("RepoDefense")[0]
        strong_ans = (
            "We encapsulate connection pooling with max size 30, enable distributed Redis caching, "
            "and add circuit breakers with exponential backoff to handle tradeoffs in latency."
        )
        out = build_deterministic_stress_evaluation(
            scenario, strong_ans, StressSessionStage.SCENARIO_ACTIVE
        )
        assert out.depth_score >= 7
        assert out.bottleneck_identified is True
        assert out.follow_up_constraint is not None
        assert out.is_terminal is False

    def test_build_deterministic_evaluation_weak(self):
        scenario = build_deterministic_stress_scenarios("RepoDefense")[0]
        weak_ans = "I do not know, it scales automatically on cloud."
        out = build_deterministic_stress_evaluation(
            scenario, weak_ans, StressSessionStage.SCENARIO_ACTIVE
        )
        assert out.depth_score <= 5
        assert out.follow_up_constraint is None
        assert out.is_terminal is True

    def test_deterministic_network_latency_jitter(self):
        scenarios = build_deterministic_stress_scenarios(
            project_name="RepoDefense",
            constraint_type=StressConstraintType.NETWORK_LATENCY_JITTER,
            max_scenarios=2,
        )
        assert len(scenarios) == 1
        assert scenarios[0].constraint_type == StressConstraintType.NETWORK_LATENCY_JITTER

    def test_base_url_allowlist_and_key_leak_guards(self):
        for bad_url in ("http://169.254.169.254/latest", "https://evil.example.com/v1"):
            with pytest.raises(ValidationError):
                GenerateStressScenariosRequest(base_url=bad_url)
            with pytest.raises(ValueError):
                _drive_coro(
                    generate_stress_scenarios("RepoDefense", base_url=bad_url, api_key="user-k")
                )

        scenario = build_deterministic_stress_scenarios("RepoDefense")[0]
        with (
            patch("app.ai.stress_test_generator.settings.FREELLMAPI_API_KEY", "server-secret"),
            patch("app.ai.stress_test_generator.litellm.acompletion") as mock_completion,
        ):
            gen_res = _drive_coro(
                generate_stress_scenarios(
                    "RepoDefense", base_url="https://api.openai.com/v1", api_key=None
                )
            )
            eval_res = _drive_coro(
                evaluate_stress_defense(
                    scenario,
                    "Use connection pooling and Redis.",
                    base_url="https://api.openai.com/v1",
                    api_key=None,
                )
            )
        mock_completion.assert_not_called()
        assert len(gen_res) >= 1
        assert eval_res.depth_score >= 4


class TestStressEndpoints:
    """Integration tests for FastAPI stress test endpoints."""

    def setup_method(self):
        self._saved_state = snapshot_stress_state()
        clear_all_stress_state()
        self.user_id = uuid.uuid4()
        self.user = User(id=self.user_id, email="dev@repodefense.dev")
        self.project_id = uuid.uuid4()
        self.project = Project(id=self.project_id, user_id=self.user_id, name="ScalingRepo")

    def teardown_method(self):
        restore_stress_state(self._saved_state)

    def _mock_db(self, project_found=True):
        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalar_one_or_none.return_value = self.project if project_found else None
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_res.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=exec_res)
        return db

    def test_get_or_generate_scenarios_success(self):
        db = self._mock_db(project_found=True)
        req = GenerateStressScenariosRequest(max_scenarios=3, api_key="")
        resp = _drive_coro(
            get_or_generate_stress_scenarios(self.project_id, req, current_user=self.user, db=db)
        )
        assert resp.total_scenarios >= 1
        assert resp.project_id == str(self.project_id)
        assert self.project_id in project_stress_cache

    def test_get_or_generate_scenarios_not_found(self):
        db = self._mock_db(project_found=False)
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(
                get_or_generate_stress_scenarios(
                    self.project_id, None, current_user=self.user, db=db
                )
            )
        assert exc_info.value.status_code == 404

    def test_full_stress_defense_flow(self):
        db = self._mock_db(project_found=True)
        scen_resp = _drive_coro(
            get_or_generate_stress_scenarios(
                self.project_id,
                GenerateStressScenariosRequest(api_key=""),
                current_user=self.user,
                db=db,
            )
        )
        scenario = scen_resp.scenarios[0]
        session = _drive_coro(
            start_stress_defense_session(
                self.project_id,
                StartStressDefenseRequest(scenario_id=scenario.id),
                current_user=self.user,
                db=db,
            )
        )
        assert session.stage == StressSessionStage.SCENARIO_ACTIVE
        assert len(session.turns) == 1

        fetched = _drive_coro(get_stress_session(session.session_id, current_user=self.user))
        assert fetched.session_id == session.session_id

        strong_ans = (
            "We configure an async connection pool with size 20, use Redis cache for "
            "read replicas, and shed excess traffic with a token bucket rate limiter "
            "to balance latency tradeoffs."
        )
        t1_resp = _drive_coro(
            submit_stress_defense_turn(
                session.session_id,
                SubmitStressAnswerRequest(answer=strong_ans, api_key=""),
                current_user=self.user,
            )
        )
        assert t1_resp.stage == StressSessionStage.FOLLOW_UP_CONSTRAINED
        assert len(t1_resp.turns) == 3

        t2_ans = "We implement Redis stale-while-revalidate and circuit breaker fallback to memory."
        t2_resp = _drive_coro(
            submit_stress_defense_turn(
                session.session_id,
                SubmitStressAnswerRequest(answer=t2_ans, api_key=""),
                current_user=self.user,
            )
        )
        assert t2_resp.stage == StressSessionStage.COMPLETED
        assert t2_resp.overall_score is not None

        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(
                submit_stress_defense_turn(
                    session.session_id,
                    SubmitStressAnswerRequest(answer="Extra answer", api_key=""),
                    current_user=self.user,
                )
            )
        assert exc_info.value.status_code == 400
