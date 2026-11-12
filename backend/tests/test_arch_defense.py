"""Hermetic unit and integration tests for Step 3.6a: Architecture Defense Mode."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.ai.arch_defense_generator import (
    build_deterministic_arch_evaluation,
    build_deterministic_arch_topics,
    evaluate_arch_defense,
    generate_arch_defense_topics,
)
from app.api.v1.arch_defense import (
    _arch_session_store,
    _arch_topic_catalog,
    get_arch_defense_session,
    get_or_generate_arch_topics,
    start_arch_defense_session,
    submit_arch_defense_turn,
)
from app.models.project import Project, User
from app.schemas.arch_defense import (
    ArchDefenseStage,
    ArchFocusAreaType,
    GenerateArchTopicsRequest,
    StartArchDefenseRequest,
    SubmitArchAnswerRequest,
)
from app.schemas.architecture import (
    ArchitecturalRisk,
    ArchitecturePatternType,
    ArchitectureReportResponse,
    DetectedPattern,
    PatternConfidenceTier,
)
from app.schemas.diagram import DiagramEdge, DiagramNode, DiagramResponse, DiagramType


def _run(coro):
    return asyncio.run(coro)


def _sample_report(project_id: str = "proj-1", files_count: int = 24) -> ArchitectureReportResponse:
    pat = DetectedPattern(
        pattern_type=ArchitecturePatternType.MODULAR_MONOLITH, pattern_name="Modular Monolith",
        confidence_score=0.84, tier=PatternConfidenceTier.HIGH, summary="Domain modules.",
    )
    risk = ArchitecturalRisk(
        risk_id="risk-1", severity="high", title="Tight API-to-DB Coupling",
        description="API handlers query tables directly.", recommendation="Route via services.",
    )
    return ArchitectureReportResponse(
        project_id=project_id, project_name="RepoDefense", primary_pattern=pat,
        all_patterns=[pat], architectural_risks=[risk],
        directory_summary={"api": 6, "services": 8}, total_files_analyzed=files_count,
    )


def _sample_diagram(project_id: str = "proj-1") -> DiagramResponse:
    return DiagramResponse(
        project_id=project_id, project_name="RepoDefense", diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code="flowchart TD\n  api[FastAPI API] --> svc[Services]",
        nodes=[
            DiagramNode(node_id="api", label="FastAPI API", node_type="backend", subgraph="API"),
            DiagramNode(node_id="svc", label="Services", node_type="service", subgraph="Core"),
        ],
        edges=[DiagramEdge(source_id="api", target_id="svc", label="calls")],
        is_fallback=True, summary="Layered topology.",
    )


class TestArchDefenseSchemas:
    """Tests for schemas and SSRF base_url override validation."""

    def test_ssrf_base_url_allowlist(self):
        assert (
            GenerateArchTopicsRequest(base_url="https://api.openai.com/v1").base_url
            == "https://api.openai.com/v1"
        )
        for bad in (
            "http://169.254.169.254/latest", "https://127.0.0.1/v1",
            "https://user:secret@api.openai.com/v1", "https://evil.example.com/v1",
        ):
            for fn in (
                lambda u: GenerateArchTopicsRequest(base_url=u),
                lambda u: StartArchDefenseRequest(topic_id="t-1", base_url=u),
                lambda u: SubmitArchAnswerRequest(answer="defend", base_url=u),
            ):
                with pytest.raises(ValidationError):
                    fn(bad)


class TestArchDefenseEngine:
    """Tests for topic synthesis, grounding reconciliation, key hygiene, and evaluation."""

    def test_deterministic_topics_and_focus_filtering(self):
        topics = build_deterministic_arch_topics(_sample_report(), _sample_diagram(), max_topics=4)
        assert len(topics) == 4
        assert {t.focus_area for t in topics} == set(ArchFocusAreaType)
        assert topics[0].target_nodes[0].node_id == "api"
        assert "api -> svc (calls)" in topics[0].target_nodes[0].connected_edges

        only_risk = build_deterministic_arch_topics(
            _sample_report(), _sample_diagram(), focus_area=ArchFocusAreaType.ARCHITECTURAL_RISK
        )
        assert len(only_risk) == 1
        assert only_risk[0].focus_area == ArchFocusAreaType.ARCHITECTURAL_RISK

    def test_llm_topic_reconciliation_and_fallback_on_error(self):
        payload = json.dumps([
            "skip-invalid-item",
            {
                "title": "Validate Service Boundary", "focus_area": "INVALID_AREA",
                "pattern_name": "Modular Monolith",
                "target_node_ids": ["api", "hallucinated_ghost_node"],
                "design_claim": "API delegates strictly to services.",
                "interrogation_prompt": "How is api isolated from DB models?",
                "expected_tradeoffs": ["Indirection vs maintainability"],
            },
        ])
        fake_resp = MagicMock(choices=[MagicMock(message=MagicMock(content=payload))])
        with patch(
            "app.ai.arch_defense_generator.litellm.acompletion",
            new=AsyncMock(return_value=fake_resp),
        ) as mock_llm:
            topics = _run(
                generate_arch_defense_topics(
                    _sample_report(), _sample_diagram(), api_key="k-1", max_topics=2
                )
            )
        mock_llm.assert_awaited_once()
        assert len(topics) == 1
        assert topics[0].focus_area == ArchFocusAreaType.PATTERN_CHOICE
        assert [n.node_id for n in topics[0].target_nodes] == ["api"]

        with patch(
            "app.ai.arch_defense_generator.litellm.acompletion",
            new=AsyncMock(side_effect=RuntimeError("timeout")),
        ):
            fb = _run(
                generate_arch_defense_topics(_sample_report(), _sample_diagram(), api_key="k")
            )
            assert len(fb) == 4

    def test_llm_and_deterministic_evaluation_and_key_isolation(self):
        topic = build_deterministic_arch_topics(_sample_report(), _sample_diagram())[0]
        eval_json = json.dumps({
            "depth_score": 8, "pattern_rationale_solid": True, "tradeoffs_articulated": True,
            "boundary_coherence_score": 9, "feedback": "Strong reasoning.",
            "follow_up_challenge": "What breaks under 10x team growth?", "is_terminal": False,
        })
        fake_resp = MagicMock(choices=[MagicMock(message=MagicMock(content=eval_json))])
        llm_target = "app.ai.arch_defense_generator.litellm.acompletion"
        with patch(llm_target, AsyncMock(return_value=fake_resp)):
            out_adv = _run(evaluate_arch_defense(
                topic, "Solid boundary defense.", ArchDefenseStage.TOPIC_ACTIVE, api_key="k"
            ))
            assert not out_adv.is_terminal and out_adv.follow_up_challenge is not None
            out_end = _run(evaluate_arch_defense(
                topic, "Final answer.", ArchDefenseStage.TRADEOFF_CHALLENGE, api_key="k"
            ))
            assert out_end.is_terminal and out_end.follow_up_challenge is None

        with (
            patch("app.ai.arch_defense_generator.settings.FREELLMAPI_API_KEY", "server-secret"),
            patch("app.ai.arch_defense_generator.litellm.acompletion") as mock_llm,
        ):
            topics = _run(generate_arch_defense_topics(
                _sample_report(), _sample_diagram(),
                base_url="https://api.openai.com/v1", api_key=None,
            ))
            eval_out = _run(evaluate_arch_defense(
                topic, "Explicit interface boundaries limit coupling.",
                ArchDefenseStage.TOPIC_ACTIVE, base_url="https://api.openai.com/v1", api_key="",
            ))
        mock_llm.assert_not_called()
        assert len(topics) >= 1 and eval_out.depth_score >= 4

    def test_deterministic_evaluation_strong_vs_weak(self):
        topic = build_deterministic_arch_topics(_sample_report(), _sample_diagram())[0]
        strong = (
            "We enforce a strict interface boundary between FastAPI API handlers and Services "
            "to minimize coupling, accepting extra schema mapping complexity and latency "
            "cost as deliberate tradeoffs for independent module scaling."
        )
        res_strong = build_deterministic_arch_evaluation(topic, strong)
        assert res_strong.depth_score >= 7 and not res_strong.is_terminal
        res_weak = build_deterministic_arch_evaluation(topic, "Because it felt right.")
        assert res_weak.depth_score <= 5 and res_weak.is_terminal


class TestArchDefenseRouter:
    """Integration tests for REST endpoints, FSM transitions, IDOR, and cache integrity."""

    def setup_method(self):
        self._saved_cat, self._saved_sess = dict(_arch_topic_catalog), dict(_arch_session_store)
        _arch_topic_catalog.clear()
        _arch_session_store.clear()
        self._key_patch = patch("app.ai.arch_defense_generator.settings.FREELLMAPI_API_KEY", "")
        self._key_patch.start()
        self.user_a = User(id=uuid.uuid4(), email="a@repodefense.dev")
        self.user_b = User(id=uuid.uuid4(), email="b@repodefense.dev")
        self.project_id = uuid.uuid4()
        self.project = Project(id=self.project_id, user_id=self.user_a.id, name="RepoDefense")

    def teardown_method(self):
        self._key_patch.stop()
        _arch_topic_catalog.clear()
        _arch_session_store.clear()
        _arch_topic_catalog.update(self._saved_cat)
        _arch_session_store.update(self._saved_sess)

    def _mock_db(self, owned: bool = True):
        db = AsyncMock()
        val = MagicMock(scalar_one_or_none=MagicMock(return_value=self.project if owned else None))
        db.execute.return_value = val
        return db

    def test_full_defense_fsm_and_idor_enforcement(self):
        rep, diag = _sample_report(str(self.project_id)), _sample_diagram(str(self.project_id))
        with (
            patch(
                "app.api.v1.arch_defense.detect_repository_architecture",
                AsyncMock(return_value=rep),
            ),
            patch(
                "app.api.v1.arch_defense.generate_project_architecture_diagram",
                AsyncMock(return_value=diag),
            ),
        ):
            resp = _run(get_or_generate_arch_topics(
                self.project_id, GenerateArchTopicsRequest(max_topics=3),
                self.user_a, self._mock_db(),
            ))
            assert resp.total_topics == 3
            sess = _run(start_arch_defense_session(
                self.project_id, StartArchDefenseRequest(topic_id=resp.topics[0].id),
                self.user_a, self._mock_db(),
            ))
            assert sess.stage == ArchDefenseStage.TOPIC_ACTIVE

        for coro in (
            start_arch_defense_session(
                self.project_id, StartArchDefenseRequest(topic_id="missing"),
                self.user_a, self._mock_db(),
            ),
            get_or_generate_arch_topics(self.project_id, None, self.user_b, self._mock_db(False)),
            get_arch_defense_session(sess.session_id, self.user_b),
            submit_arch_defense_turn(
                sess.session_id, SubmitArchAnswerRequest(answer="x"), self.user_b
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                _run(coro)
            assert exc.value.status_code == 404

        respond = submit_arch_defense_turn
        ans1 = (
            "Modular Monolith avoids network latency while isolating domain layer "
            "coupling behind explicit interface contracts and boundary tradeoffs."
        )
        t1 = _run(respond(sess.session_id, SubmitArchAnswerRequest(answer=ans1), self.user_a))
        assert t1.stage == ArchDefenseStage.TRADEOFF_CHALLENGE
        t2 = _run(respond(
            sess.session_id, SubmitArchAnswerRequest(answer="Boundary decouples nicely."),
            self.user_a,
        ))
        assert t2.stage == ArchDefenseStage.COMPLETED and t2.overall_score is not None
        with pytest.raises(HTTPException) as exc_done:
            _run(respond(sess.session_id, SubmitArchAnswerRequest(answer="extra"), self.user_a))
        assert exc_done.value.status_code == 400

    def test_cache_invalidation_and_override_bypass(self):
        r1, r2 = _sample_report(str(self.project_id), 10), _sample_report(str(self.project_id), 25)
        diag_mock = AsyncMock(return_value=_sample_diagram(str(self.project_id)))
        get_topics = get_or_generate_arch_topics
        with (
            patch(
                "app.api.v1.arch_defense.detect_repository_architecture",
                AsyncMock(side_effect=[r1, r1, r1, r2]),
            ),
            patch("app.api.v1.arch_defense.generate_project_architecture_diagram", diag_mock),
        ):
            _run(get_topics(self.project_id, None, self.user_a, self._mock_db()))
            _run(get_topics(self.project_id, None, self.user_a, self._mock_db()))
            assert diag_mock.await_count == 1
            with patch("app.ai.arch_defense_generator.settings.FREELLMAPI_API_KEY", "secret-key"):
                ov = GenerateArchTopicsRequest(base_url="https://api.openai.com/v1", api_key=None)
                _run(get_topics(self.project_id, ov, self.user_a, self._mock_db()))
                assert diag_mock.await_count == 2
                assert diag_mock.await_args.kwargs["api_key"] == ""
                assert diag_mock.await_args.kwargs["base_url"] is None
            _run(get_topics(self.project_id, None, self.user_a, self._mock_db()))
            assert diag_mock.await_count == 3
