"""Regression tests for PR #64 hardening: grounding, XML hygiene, diagram sync, and concurrency."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.arch_defense_generator import evaluate_arch_defense
from app.ai.arch_defense_prompts import (
    build_deterministic_arch_topics,
    build_diagram_targets,
    reconcile_llm_topics,
    sanitize_xml_content,
)
from app.analyzers.diagram import extract_mermaid_nodes_and_edges
from app.api.v1.arch_defense import (
    _arch_session_store,
    _arch_topic_catalog,
    _session_locks,
    get_or_generate_arch_topics,
    start_arch_defense_session,
    submit_arch_defense_turn,
)
from app.models.project import Project, User
from app.schemas.arch_defense import (
    ArchDefenseEvaluationOutput,
    ArchDefenseSessionState,
    ArchDefenseStage,
    ArchDefenseTurn,
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
from app.services.arch_defense_store import ensure_session_capacity
from app.services.diagram import generate_project_architecture_diagram


def _report(project_id: str = "proj-1") -> ArchitectureReportResponse:
    pat = DetectedPattern(
        pattern_type=ArchitecturePatternType.MODULAR_MONOLITH,
        pattern_name="Modular Monolith",
        confidence_score=0.86,
        tier=PatternConfidenceTier.HIGH,
        summary="Bounded modules.",
    )
    return ArchitectureReportResponse(
        project_id=project_id,
        project_name="RepoDefense",
        primary_pattern=pat,
        all_patterns=[pat],
        architectural_risks=[
            ArchitecturalRisk(
                risk_id="r-1", severity="medium", title="Boundary Creep",
                description="Direct DB access.", recommendation="Use service interface.",
            )
        ],
        directory_summary={"api": 4},
        total_files_analyzed=12,
    )


def _diagram(project_id: str = "proj-1", edges=None) -> DiagramResponse:
    return DiagramResponse(
        project_id=project_id,
        project_name="RepoDefense",
        diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code="flowchart TD\n  api[API Layer] --> svc[Core Service]",
        nodes=[
            DiagramNode(node_id="api", label="API Layer", node_type="backend", subgraph="API"),
            DiagramNode(node_id="svc", label="Core Service", node_type="service", subgraph="Core"),
        ],
        edges=edges if edges is not None else [],
        is_fallback=False,
        summary="Topology.",
    )


def test_no_fabricated_edge_claim_when_diagram_edges_empty():
    """#1: Empty diagram.edges must not produce fabricated 'n1 -> n2' connection claims."""
    topics = build_deterministic_arch_topics(_report(), _diagram(edges=[]), max_topics=4)
    flow = next(t for t in topics if t.focus_area == ArchFocusAreaType.DATA_FLOW_COUPLING)
    assert "api -> svc" not in flow.design_claim
    assert "No explicit edge" in flow.design_claim


def test_reconcile_rejects_ungrounded_targets_and_fabricated_patterns():
    """#2: LLM items lacking matching target_node_ids or known patterns must be dropped."""
    diag = _diagram(edges=[DiagramEdge(source_id="api", target_id="svc", label="calls")])
    targets = build_diagram_targets(diag)
    raw = [
        {
            "title": "Ghost Nodes", "focus_area": "PATTERN_CHOICE",
            "pattern_name": "Modular Monolith", "target_node_ids": ["nonexistent_node"],
            "design_claim": "Claim", "interrogation_prompt": "Why?",
        },
        {
            "title": "Fake Pattern", "focus_area": "PATTERN_CHOICE",
            "pattern_name": "Blockchain Mesh", "target_node_ids": ["api"],
            "design_claim": "Claim", "interrogation_prompt": "Why?",
        },
        {
            "title": "Valid Topic", "focus_area": "COMPONENT_BOUNDARY",
            "pattern_name": "Modular Monolith", "target_node_ids": ["svc"],
            "design_claim": "API calls svc.", "interrogation_prompt": "Why expose svc?",
        },
    ]
    out = reconcile_llm_topics(raw, targets, _report(), None, max_topics=4)
    assert len(out) == 1 and out[0].title == "Valid Topic"


@pytest.mark.anyio
async def test_diagram_nodes_edges_derived_from_llm_mermaid_code():
    """#3: generate_project_architecture_diagram returns nodes/edges matching mermaid_code IDs."""
    mermaid = (
        'flowchart TD\n  subgraph edge["Edge Tier"]\n    gw["Gateway"]\n'
        '    worker["Worker"]\n  end\n  gw -->|"dispatches"| worker'
    )
    nodes, edges = extract_mermaid_nodes_and_edges(mermaid)
    assert {n.node_id for n in nodes} == {"gw", "worker"}
    assert len(edges) == 1 and edges[0].source_id == "gw" and edges[0].target_id == "worker"

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(all=MagicMock(return_value=[])),
        MagicMock(all=MagicMock(return_value=[])),
    ]
    proj = Project(id=uuid.uuid4(), user_id=uuid.uuid4(), name="RepoDefense")
    fake_resp = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({"mermaid_code": mermaid})))]
    )
    with patch("app.services.diagram.litellm.acompletion", AsyncMock(return_value=fake_resp)):
        diag = await generate_project_architecture_diagram(proj, db, api_key="k-test")
    assert not diag.is_fallback
    assert {n.node_id for n in diag.nodes} == {"gw", "worker"}
    assert diag.edges[0].source_id == "gw" and diag.edges[0].target_id == "worker"


@pytest.mark.anyio
async def test_xml_escape_preserves_mermaid_arrows_and_full_8000_char_answer():
    """#4 & #5: Closing XML tags are escaped without mangling -->, and 7500 chars are kept."""
    cleaned = sanitize_xml_content("a --> b </diagram_mermaid> end", 1600)
    assert "-->" in cleaned
    assert "</diagram_mermaid>" not in cleaned and "&lt;/diagram_mermaid>" in cleaned

    topic = build_deterministic_arch_topics(_report(), _diagram())[0]
    long_ans = "boundary coupling layer tradeoff " * 220 + "</candidate_defense>"
    assert 6500 < len(long_ans) <= 8000
    eval_json = json.dumps({
        "depth_score": 8, "pattern_rationale_solid": True, "tradeoffs_articulated": True,
        "boundary_coherence_score": 8, "feedback": "Good.", "is_terminal": True,
    })
    fake_resp = MagicMock(choices=[MagicMock(message=MagicMock(content=eval_json))])
    target = "app.ai.arch_defense_generator.litellm.acompletion"
    with patch(target, AsyncMock(return_value=fake_resp)) as m:
        await evaluate_arch_defense(topic, long_ans, ArchDefenseStage.TOPIC_ACTIVE, api_key="k")
    sent_prompt = m.await_args.kwargs["messages"][1]["content"]
    assert len(long_ans) - 10 < len(sent_prompt) and "&lt;/candidate_defense>" in sent_prompt


@pytest.mark.anyio
async def test_router_hardening_aggregation_isolation_capacity_and_locking():
    """#6-#10: Multi-turn scoring, cache isolation, start overrides, capacity & locking."""
    _arch_topic_catalog.clear()
    _arch_session_store.clear()
    _session_locks.clear()
    try:
        uid, pid = uuid.uuid4(), uuid.uuid4()
        user = User(id=uid, email="h@repodefense.dev")
        proj = Project(id=pid, user_id=uid, name="RepoDefense")
        rep = _report(str(pid))
        d_def = _diagram(str(pid), [DiagramEdge(source_id="api", target_id="svc")])
        d_ovr = DiagramResponse(
            project_id=str(pid), project_name="RepoDefense", diagram_type=DiagramType.FLOWCHART_TD,
            mermaid_code="flowchart TD\n  ovr[Override Node]",
            nodes=[DiagramNode(node_id="ovr", label="Override Node", node_type="service")],
            edges=[], is_fallback=False, summary="Override topology.",
        )

        def mock_db():
            db = AsyncMock()
            db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=proj))
            return db

        rep_patch = "app.api.v1.arch_defense.detect_repository_architecture"
        diag_patch = "app.api.v1.arch_defense.generate_project_architecture_diagram"
        with (
            patch(rep_patch, AsyncMock(return_value=rep)),
            patch(diag_patch, AsyncMock(side_effect=[d_def, d_ovr])),
            patch("app.ai.arch_defense_generator.settings.FREELLMAPI_API_KEY", ""),
        ):
            r_def = await get_or_generate_arch_topics(pid, None, user, mock_db())
            r_ovr = await get_or_generate_arch_topics(
                pid, GenerateArchTopicsRequest(model="gpt-4o-mini"), user, mock_db()
            )
            assert "ovr[Override Node]" not in r_def.mermaid_code
            assert "ovr[Override Node]" in r_ovr.mermaid_code

            with pytest.raises(HTTPException) as exc_ov:
                ov_req = StartArchDefenseRequest(topic_id=r_def.topics[0].id, model="x")
                await start_arch_defense_session(pid, ov_req, user, mock_db())
            assert exc_ov.value.status_code == 400

            s_ovr = await start_arch_defense_session(
                pid, StartArchDefenseRequest(topic_id=r_ovr.topics[0].id), user, mock_db()
            )
            assert s_ovr.mermaid_code == d_ovr.mermaid_code

        # #6 & #10: Concurrent /respond calls serialize and aggregate Turn 1 + Turn 2 scores.
        s1_out = ArchDefenseEvaluationOutput(
            depth_score=9, pattern_rationale_solid=True, tradeoffs_articulated=True,
            boundary_coherence_score=9, feedback="Strong", follow_up_challenge="Scale?",
            is_terminal=False,
        )
        s2_out = ArchDefenseEvaluationOutput(
            depth_score=5, pattern_rationale_solid=False, tradeoffs_articulated=True,
            boundary_coherence_score=5, feedback="Okay", follow_up_challenge=None, is_terminal=True,
        )
        seen_stages = []

        async def slow_eval(**kwargs):
            seen_stages.append(kwargs["stage"])
            await asyncio.sleep(0.02)
            return s1_out if kwargs["stage"] == ArchDefenseStage.TOPIC_ACTIVE else s2_out

        with patch("app.api.v1.arch_defense.evaluate_arch_defense", side_effect=slow_eval):
            sid = s_ovr.session_id
            res_a, res_b = await asyncio.gather(
                submit_arch_defense_turn(sid, SubmitArchAnswerRequest(answer="turn 1"), user),
                submit_arch_defense_turn(sid, SubmitArchAnswerRequest(answer="turn 2"), user),
            )
        assert seen_stages == [ArchDefenseStage.TOPIC_ACTIVE, ArchDefenseStage.TRADEOFF_CHALLENGE]
        assert res_b.stage == ArchDefenseStage.COMPLETED
        assert res_b.overall_score == 7.0  # ((9+9)/2 + (5+5)/2) / 2 == 7.0
        assert res_b.pattern_rationale_solid is True

        # #9: Completed sessions expire before new ones; active-only full store raises 503.
        ensure_session_capacity(max_sessions=1)
        assert s_ovr.session_id not in _arch_session_store
        q_turn = ArchDefenseTurn(
            role="interviewer", content="Q", stage=ArchDefenseStage.TOPIC_ACTIVE
        )
        active_sess = ArchDefenseSessionState(
            session_id="act-1", project_id=str(pid), topic=r_def.topics[0],
            mermaid_code="flowchart TD", diagram_summary="s",
            primary_pattern_name="Modular Monolith", stage=ArchDefenseStage.TOPIC_ACTIVE,
            turns=[q_turn],
        )
        _arch_session_store["act-1"] = (uid, active_sess)
        with pytest.raises(HTTPException) as exc_cap:
            ensure_session_capacity(max_sessions=1)
        assert exc_cap.value.status_code == 503 and "act-1" in _arch_session_store
    finally:
        _arch_topic_catalog.clear()
        _arch_session_store.clear()
        _session_locks.clear()
