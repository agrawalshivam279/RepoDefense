"""Hermetic unit and integration tests for Step 3.4a: Incident Simulation Engine."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.ai.incident_generator import (
    _build_deterministic_scenarios,
    evaluate_incident_defense_turn,
)
from app.api.v1.incident_simulation import (
    generate_scenarios_endpoint,
    get_incident_session_endpoint,
    incident_session_store,
    project_scenarios_cache,
    respond_to_incident_turn_endpoint,
    start_incident_session_endpoint,
)
from app.models.project import Project, User
from app.schemas.incident import (
    ChaosTarget,
    FailureCategory,
    GenerateScenariosRequest,
    IncidentScenario,
    IncidentSeverity,
    IncidentStage,
    StartIncidentDefenseRequest,
    SubmitIncidentAnswerRequest,
)


def _drive_coro(coro):
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


class TestIncidentSchemasAndFallbacks:
    """Tests for Pydantic v2 schemas and deterministic chaos scenario synthesis."""

    def test_schema_instantiation(self):
        target = ChaosTarget(
            file_path="src/db.py", symbol_name="get_session", component_type="database"
        )
        scenario = IncidentScenario(
            title="Database Connection Pool Starvation",
            category=FailureCategory.DATABASE_OUTAGE,
            severity=IncidentSeverity.P0_CRITICAL,
            hypothetical_trigger="Traffic spike",
            symptoms=["504 gateway timeout"],
            grounded_target=target,
            incident_question="How does your code handle this?",
            evaluation_criteria=["Circuit breaker", "Pool limit"],
        )
        assert scenario.category == FailureCategory.DATABASE_OUTAGE
        assert scenario.severity == IncidentSeverity.P0_CRITICAL
        assert len(scenario.evaluation_criteria) == 2

    def test_deterministic_scenarios_category_filter(self):
        evidence = [
            {"file_path": "backend/app/core/database.py", "symbol_name": "get_db", "type": "db"}
        ]
        scenarios = _build_deterministic_scenarios(
            evidence, category=FailureCategory.DATABASE_OUTAGE, limit=2
        )
        assert len(scenarios) >= 1
        assert scenarios[0].category == FailureCategory.DATABASE_OUTAGE
        assert "Database" in scenarios[0].title
        assert "get_db" in scenarios[0].grounded_target.symbol_name

    def test_deterministic_scenarios_all_categories(self):
        evidence = []
        scenarios = _build_deterministic_scenarios(evidence, category=None, limit=3)
        assert len(scenarios) == 3
        cats = {s.category for s in scenarios}
        assert FailureCategory.DATABASE_OUTAGE in cats
        assert FailureCategory.DEPENDENCY_TIMEOUT in cats


class TestIncidentTurnEvaluation:
    """Tests for multi-turn incident defense evaluation and escalation logic."""

    def setup_method(self):
        self.scenario = _build_deterministic_scenarios(
            [], category=FailureCategory.DATABASE_OUTAGE, limit=1
        )[0]

    def test_turn_1_evaluation_and_chaos_escalation(self):
        answer = (
            "I will configure a strict connection pool timeout and implement a circuit breaker "
            "with exponential backoff."
        )
        res = evaluate_incident_defense_turn(
            self.scenario, turn_index=1, max_turns=3, candidate_answer=answer
        )
        assert res["score"] > 60.0
        assert res["next_stage"] == IncidentStage.ESCALATED
        assert "CHAOS ESCALATION" in res["escalation_injected"]

    def test_turn_2_mitigation(self):
        answer = (
            "We will add jitter to retries, enforce client rate limits, and shed non-critical load."
        )
        res = evaluate_incident_defense_turn(
            self.scenario, turn_index=2, max_turns=3, candidate_answer=answer
        )
        assert res["next_stage"] == IncidentStage.MITIGATED
        assert "POSTMORTEM" in res["next_prompt"].upper()

    def test_turn_3_postmortem(self):
        answer = (
            "Our postmortem mandates load tests, alerts at 80% pool utilization, and canary gates."
        )
        res = evaluate_incident_defense_turn(
            self.scenario, turn_index=3, max_turns=3, candidate_answer=answer
        )
        assert res["next_stage"] == IncidentStage.POSTMORTEM
        assert res["escalation_injected"] is None


class TestIncidentEndpoints:
    """Integration tests for FastAPI incident simulation endpoints."""

    def setup_method(self):
        incident_session_store.clear()
        project_scenarios_cache.clear()
        self.user_id = uuid.uuid4()
        self.user = User(id=self.user_id, email="dev@example.com")
        self.project_id = uuid.uuid4()
        self.project = Project(id=self.project_id, user_id=self.user_id, name="TestRepo")

    def _mock_db(self, project_found=True):
        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalar_one_or_none.return_value = self.project if project_found else None
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_res.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=exec_res)
        return db

    def test_generate_scenarios_success(self):
        db = self._mock_db(project_found=True)
        req = GenerateScenariosRequest(category=FailureCategory.DATABASE_OUTAGE, limit=2)
        resp = _drive_coro(
            generate_scenarios_endpoint(self.project_id, req, current_user=self.user, db=db)
        )
        assert resp.total_scenarios >= 1
        assert resp.project_id == self.project_id
        assert self.project_id in project_scenarios_cache

    def test_generate_scenarios_project_not_found(self):
        db = self._mock_db(project_found=False)
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(
                generate_scenarios_endpoint(
                    self.project_id, GenerateScenariosRequest(), current_user=self.user, db=db
                )
            )
        assert exc_info.value.status_code == 404

    def test_full_incident_defense_session_flow(self):
        db = self._mock_db(project_found=True)

        # 1. Start Session
        start_req = StartIncidentDefenseRequest(category=FailureCategory.DATABASE_OUTAGE)
        session = _drive_coro(
            start_incident_session_endpoint(
                self.project_id, start_req, current_user=self.user, db=db
            )
        )
        assert session.stage == IncidentStage.TRIAGE
        assert session.current_turn_index == 1
        assert len(session.turns) == 1
        session_id = session.id

        # 2. Get Session
        fetched = _drive_coro(
            get_incident_session_endpoint(session_id, current_user=self.user, db=db)
        )
        assert fetched.id == session_id

        # 3. Respond Turn 1 -> Escalated
        ans1 = SubmitIncidentAnswerRequest(
            answer="We implement circuit breaker fail-fast logic and connection pooling limits."
        )
        s1 = _drive_coro(
            respond_to_incident_turn_endpoint(session_id, ans1, current_user=self.user, db=db)
        )
        assert s1.stage == IncidentStage.ESCALATED
        assert s1.current_turn_index == 2
        assert len(s1.turns) == 2

        # 4. Respond Turn 2 -> Mitigated
        ans2 = SubmitIncidentAnswerRequest(
            answer="We introduce retry backoff with full jitter and a token bucket rate limiter."
        )
        s2 = _drive_coro(
            respond_to_incident_turn_endpoint(session_id, ans2, current_user=self.user, db=db)
        )
        assert s2.stage == IncidentStage.MITIGATED
        assert s2.current_turn_index == 3
        assert len(s2.turns) == 3

        # 5. Respond Turn 3 -> Postmortem & Final Score
        ans3 = SubmitIncidentAnswerRequest(
            answer=(
                "Postmortem action items: add automated chaos tests, circuit breaker alerts, "
                "healthcheck timeout monitors, and a dead letter queue retry mechanism."
            )
        )
        s3 = _drive_coro(
            respond_to_incident_turn_endpoint(session_id, ans3, current_user=self.user, db=db)
        )
        assert s3.stage == IncidentStage.POSTMORTEM
        assert s3.overall_score is not None
        assert s3.overall_score > 40.0
        assert s3.postmortem_summary is not None
        assert "INCIDENT POSTMORTEM" in s3.postmortem_summary

        # 6. Reject responses once completed
        with pytest.raises(HTTPException) as exc_info:
            _drive_coro(
                respond_to_incident_turn_endpoint(session_id, ans3, current_user=self.user, db=db)
            )
        assert exc_info.value.status_code == 400
