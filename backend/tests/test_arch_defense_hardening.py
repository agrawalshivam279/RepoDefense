"""Regression tests for PR #64 hardening: grounding, Mermaid extraction, concurrency & caps."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.ai.arch_defense_generator import evaluate_arch_defense
from app.ai.arch_defense_prompts import (
    build_deterministic_arch_evaluation,
    build_deterministic_arch_topics,
    build_diagram_targets,
    reconcile_llm_topics,
    sanitize_xml_content,
)
from app.analyzers.diagram import extract_mermaid_nodes_and_edges
from app.api.v1.arch_defense import (
    _arch_session_store,
    _arch_topic_catalog,
    _project_locks,
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
        pattern_name="Modular Monolith", confidence_score=0.86,
        tier=PatternConfidenceTier.HIGH, summary="Bounded modules.",
    )
    risk = ArchitecturalRisk(
        risk_id="r-1", severity="medium", title="Boundary Creep",
        description="Direct DB access.", recommendation="Use service interface.",
    )
    return ArchitectureReportResponse(
        project_id=project_id, project_name="RepoDefense", primary_pattern=pat,
        all_patterns=[pat], architectural_risks=[risk],
        directory_summary={"api": 4}, total_files_analyzed=12,
    )


def _diagram(project_id: str = "proj-1", edges=None, single: bool = False) -> DiagramResponse:
    n1 = DiagramNode(node_id="api", label="API Layer", node_type="backend", subgraph="API")
    n2 = DiagramNode(node_id="svc", label="Core Service", node_type="service", subgraph="Core")
    n3 = DiagramNode(node_id="db", label="Postgres DB", node_type="database", subgraph="Data")
    nodes = [n1] if single else [n1, n2, n3]
    mermaid = (
        "flowchart TD\n  api[API Layer]" if single
        else ("flowchart TD\n  api --> svc\n  svc --> db" if edges
              else "flowchart TD\n  api[API Layer]\n  svc[Core Service]\n  db[Postgres DB]")
    )
    return DiagramResponse(
        project_id=project_id, project_name="RepoDefense", diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code=mermaid, nodes=nodes, edges=edges if edges is not None else [],
        is_fallback=False, summary="Topology.",
    )


def test_deterministic_topics_grounding_single_node_and_edge_endpoints():
    """#1, #2 & #10: No fake edges, valid single-node questions, exact edge endpoints."""
    topics_no_edge = build_deterministic_arch_topics(_report(), _diagram(edges=[]), max_topics=4)
    flow_empty = next(
        t for t in topics_no_edge if t.focus_area == ArchFocusAreaType.DATA_FLOW_COUPLING
    )
    assert "api -> svc" not in flow_empty.design_claim
    assert "No explicit edge" in flow_empty.design_claim

    topics_one = build_deterministic_arch_topics(_report(), _diagram(edges=[], single=True))
    bnd_one = next(t for t in topics_one if t.focus_area == ArchFocusAreaType.COMPONENT_BOUNDARY)
    assert "and 'API Layer'" not in bnd_one.design_claim

    topics_edge = build_deterministic_arch_topics(
        _report(), _diagram(edges=[DiagramEdge(source_id="svc", target_id="db", label="SQL")]),
    )
    flow_edge = next(t for t in topics_edge if t.focus_area == ArchFocusAreaType.DATA_FLOW_COUPLING)
    assert [n.node_id for n in flow_edge.target_nodes] == ["svc", "db"]


def test_reconcile_rejects_ungrounded_and_malformed_llm_fields():
    """#2 & #3 (Hardening): Reject ghost targets, bad patterns, and malformed list fields."""
    diag = _diagram(edges=[DiagramEdge(source_id="api", target_id="svc", label="calls")])
    targets = build_diagram_targets(diag)
    raw = [
        {
            "title": "Malformed ids", "focus_area": "PATTERN_CHOICE",
            "pattern_name": "Modular Monolith", "target_node_ids": "api",
            "design_claim": "Claim", "interrogation_prompt": "Why?",
        },
        {
            "title": "Ghost", "focus_area": "PATTERN_CHOICE", "pattern_name": "Modular Monolith",
            "target_node_ids": ["ghost"], "design_claim": "C", "interrogation_prompt": "Q",
        },
        {
            "title": "Fake Pat", "focus_area": "PATTERN_CHOICE", "pattern_name": "Grid",
            "target_node_ids": ["api"], "design_claim": "C", "interrogation_prompt": "Q",
        },
        {
            "title": "Valid Topic", "focus_area": "COMPONENT_BOUNDARY",
            "pattern_name": "Modular Monolith", "target_node_ids": ["svc"],
            "design_claim": "API calls svc.", "interrogation_prompt": "Why expose svc?",
            "expected_tradeoffs": ["Latency"], "risk_references": ["r-1"],
        },
    ]
    out = reconcile_llm_topics(raw, targets, _report(), None, max_topics=4)
    assert len(out) == 1 and out[0].title == "Valid Topic"


@pytest.mark.anyio
async def test_mermaid_extraction_inline_labels_and_late_subgraph():
    """#4, #5 & #6: Inline edge labels, unlabelled subgraph ID, late node subgraph update."""
    mermaid = (
        'flowchart TD\n  api["FastAPI (v2)"] --> worker\n'
        '  subgraph core\n    worker["Queue Worker (ARQ)"]\n  end'
    )
    nodes, edges = extract_mermaid_nodes_and_edges(mermaid)
    by_id = {n.node_id: n for n in nodes}
    assert by_id["api"].label == "FastAPI (v2)"
    assert by_id["worker"].label == "Queue Worker (ARQ)"
    assert by_id["worker"].subgraph == "core" and by_id["worker"].node_type == "queue"
    assert len(edges) == 1 and edges[0].source_id == "api" and edges[0].target_id == "worker"

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
    assert not diag.is_fallback and {n.node_id for n in diag.nodes} == {"api", "worker"}


@pytest.mark.anyio
async def test_xml_escape_and_full_8000_char_answer_and_offline_cue():
    """#4, #5 & offline scoring: Neutralize closing XML tags in ctx/mermaid/answer."""
    cleaned = sanitize_xml_content("a --> b </diagram_mermaid> end", 1600)
    assert "-->" in cleaned and "&lt;/diagram_mermaid>" in cleaned

    topic = build_deterministic_arch_topics(_report(), _diagram())[0]
    spam = "boundary coupling layer tradeoff " * 5
    assert build_deterministic_arch_evaluation(topic, spam).depth_score == 6

    long_ans = "boundary coupling api tradeoff " * 230 + "</candidate_defense>"
    assert 6500 < len(long_ans) <= 8000
    eval_json = json.dumps({
        "depth_score": 8, "pattern_rationale_solid": True, "tradeoffs_articulated": True,
        "boundary_coherence_score": 8, "feedback": "Good.", "is_terminal": True,
    })
    fake_resp = MagicMock(choices=[MagicMock(message=MagicMock(content=eval_json))])
    target = "app.ai.arch_defense_generator.litellm.acompletion"
    with patch(target, AsyncMock(return_value=fake_resp)) as m:
        await evaluate_arch_defense(topic, long_ans, ArchDefenseStage.TOPIC_ACTIVE, api_key="k")
    sent = m.await_args.kwargs["messages"][1]["content"]
    assert len(long_ans) - 10 < len(sent) and "&lt;/candidate_defense>" in sent


@pytest.mark.anyio
async def test_router_hardening_isolation_atomic_turn_and_capacity():
    """#6-#11: Store restore, concurrent topics, atomic commit, locking & per-user cap."""
    saved_cat, saved_sess = dict(_arch_topic_catalog), dict(_arch_session_store)
    saved_locks, saved_plocks = dict(_session_locks), dict(_project_locks)
    for st in (_arch_topic_catalog, _arch_session_store, _session_locks, _project_locks):
        st.clear()
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
            edges=[], is_fallback=False, summary="Override.",
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
            r_def, r_ovr = await asyncio.gather(
                get_or_generate_arch_topics(pid, None, user, mock_db()),
                get_or_generate_arch_topics(
                    pid, GenerateArchTopicsRequest(model="gpt-4o-mini"), user, mock_db()
                ),
            )
            assert len(_arch_topic_catalog[pid].topics) >= len(r_def.topics) + len(r_ovr.topics)
            s_ovr = await start_arch_defense_session(
                pid, StartArchDefenseRequest(topic_id=r_ovr.topics[0].id), user, mock_db()
            )
            assert s_ovr.mermaid_code == d_ovr.mermaid_code

        # #8: Failed/cancelled evaluation leaves no candidate turn visible.
        with patch(
            "app.api.v1.arch_defense.evaluate_arch_defense",
            AsyncMock(side_effect=asyncio.CancelledError()),
        ):
            with pytest.raises(asyncio.CancelledError):
                await submit_arch_defense_turn(
                    s_ovr.session_id, SubmitArchAnswerRequest(answer="aborted"), user
                )
        assert len(s_ovr.turns) == 1

        # #6 & #10: Serialized concurrent turns aggregate Turn 1 + Turn 2 scores.
        s1_out = ArchDefenseEvaluationOutput(
            depth_score=9, pattern_rationale_solid=True, tradeoffs_articulated=True,
            boundary_coherence_score=9, feedback="Strong", follow_up_challenge="Scale?",
            is_terminal=False,
        )
        s2_out = ArchDefenseEvaluationOutput(
            depth_score=5, pattern_rationale_solid=False, tradeoffs_articulated=True,
            boundary_coherence_score=5, feedback="Okay", is_terminal=True,
        )
        stages = []

        async def slow_eval(**kw):
            stages.append(kw["stage"])
            await asyncio.sleep(0.02)
            return s1_out if kw["stage"] == ArchDefenseStage.TOPIC_ACTIVE else s2_out

        with patch("app.api.v1.arch_defense.evaluate_arch_defense", side_effect=slow_eval):
            sid = s_ovr.session_id
            _, r2 = await asyncio.gather(
                submit_arch_defense_turn(sid, SubmitArchAnswerRequest(answer="t1"), user),
                submit_arch_defense_turn(sid, SubmitArchAnswerRequest(answer="t2"), user),
            )
        assert stages == [ArchDefenseStage.TOPIC_ACTIVE, ArchDefenseStage.TRADEOFF_CHALLENGE]
        assert r2.overall_score == 7.0 and r2.pattern_rationale_solid is True

        # #9: Completed expire cleanly; per-user cap (429) & active cap (503) protect active.
        ensure_session_capacity(max_sessions=1)
        assert s_ovr.session_id not in _arch_session_store
        q = ArchDefenseTurn(role="interviewer", content="Q", stage=ArchDefenseStage.TOPIC_ACTIVE)
        _arch_session_store["act-1"] = (uid, ArchDefenseSessionState(
            session_id="act-1", project_id=str(pid), topic=r_def.topics[0],
            mermaid_code="flowchart TD", diagram_summary="s",
            primary_pattern_name="Modular Monolith",
            stage=ArchDefenseStage.TOPIC_ACTIVE, turns=[q],
        ))
        with pytest.raises(HTTPException) as exc_u:
            ensure_session_capacity(user_id=uid, max_sessions=500, max_per_user=1)
        assert exc_u.value.status_code == 429
        with pytest.raises(HTTPException) as exc_g:
            ensure_session_capacity(user_id=uuid.uuid4(), max_sessions=1, max_per_user=5)
        assert exc_g.value.status_code == 503 and "act-1" in _arch_session_store
    finally:
        for st, sv in (
            (_arch_topic_catalog, saved_cat), (_arch_session_store, saved_sess),
            (_session_locks, saved_locks), (_project_locks, saved_plocks),
        ):
            st.clear()
            st.update(sv)
