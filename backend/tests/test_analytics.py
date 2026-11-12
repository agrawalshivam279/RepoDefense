"""Hermetic unit and ASGI integration tests for Step 3.7a Analytics API & Service."""

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import DefenseSessionStore
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.schemas.analytics import DefenseModeKey
from app.schemas.arch_defense import (
    ArchDefenseSessionState,
    ArchDefenseStage,
    ArchDefenseTopic,
    ArchFocusAreaType,
)
from app.schemas.commit_defense import CommitDefenseSessionState
from app.schemas.coverage import (
    CoverageStatus,
    CoverageTier,
    ModuleCoverageItem,
    ProjectCoverageResponse,
)
from app.schemas.defense import DefenseQuestionProgress, DefenseSessionState, DefenseStage
from app.schemas.incident import (
    ChaosTarget,
    FailureCategory,
    IncidentDefenseSessionState,
    IncidentScenario,
    IncidentSeverity,
    IncidentStage,
)
from app.schemas.pr_defense import PRDefenseSessionState
from app.schemas.question import GroundedQuestion, QuestionCategory
from app.schemas.stress_test import (
    StressConstraintType,
    StressDefenseSessionState,
    StressSessionStage,
    StressTarget,
    StressTestScenario,
)
from app.schemas.tech_audit import TechAuditReportResponse
from app.services.analytics import build_project_analytics, build_workspace_analytics
from app.services.analytics_extractors import normalize_score


def _make_fake_db(project=None, projects=None, snapshot_id=None, lang_rows=None):
    db = AsyncMock()
    if projects is not None:
        all_mock = MagicMock(all=MagicMock(return_value=projects))
        db.execute = AsyncMock(side_effect=[MagicMock(scalars=MagicMock(return_value=all_mock))])
        return db

    proj_mock = MagicMock(scalar_one_or_none=MagicMock(return_value=project))
    snap_first = MagicMock(first=MagicMock(return_value=snapshot_id))
    responses = [proj_mock, MagicMock(scalars=MagicMock(return_value=snap_first))]
    if snapshot_id is not None:
        responses.append(MagicMock(all=MagicMock(return_value=lang_rows or [])))
    db.execute = AsyncMock(side_effect=responses)
    return db


def _proj(pid: uuid.UUID, uid: uuid.UUID, name: str = "RepoDefense", status: str = "analyzed"):
    url = "https://github.com/a/b"
    return Project(id=pid, user_id=uid, name=name, github_url=url, status=status)


async def _populate_store(store: DefenseSessionStore, pid: str, other_pid: str) -> None:
    q = GroundedQuestion(
        id="q-1", category=QuestionCategory.ARCHITECTURE, context_hint="app/api/v1/projects.py",
        question_text="Why isolate service modules?", cited_files=["app/api/v1/projects.py"],
    )
    await store.save(
        DefenseSessionState(
            session_id="core-1", project_id=pid,
            status=DefenseStage.SESSION_COMPLETED, total_questions=1,
            questions=[DefenseQuestionProgress(question=q)],
            topic_confidence={"architecture": 0.85},
            overall_score=8.0, updated_at="2026-11-12T10:00:00Z",
        )
    )
    await store.save(
        PRDefenseSessionState(
            session_id="pr-1", project_id=pid, status=DefenseStage.SESSION_COMPLETED, pr_number=42,
            pr_title="Harden JWT", pr_html_url="https://github.com/o/r/pull/42", pr_author="dev",
            pr_analysis_summary="JWT", overall_score=6.0, updated_at="2026-11-12T11:00:00Z",
        )
    )
    await store.save(
        CommitDefenseSessionState(
            session_id="commit-1", project_id=pid, status=DefenseStage.QUESTION_ACTIVE,
            commit_hash="abc1234", commit_message="Refactor query", commit_author="dev",
            commit_html_url="https://github.com/o/r/commit/abc1234",
            commit_analysis_summary="HNSW", updated_at="2026-11-12T11:30:00Z",
        )
    )
    await store.save(
        DefenseSessionState(
            session_id="other-1", project_id=other_pid,
            status=DefenseStage.SESSION_COMPLETED, overall_score=2.0,
        )
    )


def _extra_stores(pid: uuid.UUID):
    stress = {
        "stress-1": StressDefenseSessionState(
            session_id="stress-1", project_id=str(pid), stage=StressSessionStage.COMPLETED,
            overall_score=9.0, updated_at="2026-11-12T12:00:00Z",
            scenario=StressTestScenario(
                title="10x Spike", constraint_type=StressConstraintType.CONCURRENCY_SPIKE,
                target=StressTarget(symbol_name="login", file_path="app/auth.py"),
                context_description="Auth", hypothetical_prompt="What fails at 10k RPS?",
            ),
        )
    }
    inc_id = uuid.uuid4()
    incident = {
        inc_id: IncidentDefenseSessionState(
            id=inc_id, project_id=pid, stage=IncidentStage.POSTMORTEM, overall_score=75.0,
            scenario=IncidentScenario(
                title="Redis Pool Exhaustion", category=FailureCategory.CACHE_FAILURE,
                severity=IncidentSeverity.P0_CRITICAL, hypothetical_trigger="OOM",
                grounded_target=ChaosTarget(file_path="app/core/redis.py"),
                incident_question="How do requests degrade?",
            ),
        )
    }
    arch = {
        "arch-1": ArchDefenseSessionState(
            session_id="arch-1", project_id=str(pid), mermaid_code="flowchart TD\nA-->B",
            diagram_summary="Summary", primary_pattern_name="Modular Monolith",
            stage=ArchDefenseStage.COMPLETED, overall_score=7.0, boundary_coherence_score=8.0,
            updated_at="2026-11-12T13:00:00Z",
            topic=ArchDefenseTopic(
                id="t-1", title="Layering", focus_area=ArchFocusAreaType.COMPONENT_BOUNDARY,
                pattern_name="Modular Monolith", severity_or_confidence="HIGH",
                design_claim="Strict layering", interrogation_prompt="Why single service?",
            ),
        )
    }
    return stress, incident, arch


def test_normalize_score_clamping():
    assert normalize_score(8.5, scale_10=True) == 85.0
    assert normalize_score(120.0, scale_10=False) == 100.0
    assert normalize_score(-3.0, scale_10=True) == 0.0
    assert normalize_score(None, scale_10=True) is None


def _run(coro):
    return asyncio.run(coro)


def test_build_project_analytics_aggregates_all_modes_and_ground_truth():
    async def _impl():
        uid, pid, other_pid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        proj = _proj(pid, uid)
        langs = [
            SimpleNamespace(language="python", file_count=10, total_lines=800),
            SimpleNamespace(language="typescript", file_count=5, total_lines=200),
        ]
        db = _make_fake_db(project=proj, snapshot_id=uuid.uuid4(), lang_rows=langs)

        fsm = DefenseSessionStore()
        await _populate_store(fsm, str(pid), str(other_pid))
        stress_store, incident_store, arch_store = _extra_stores(pid)

        mod = ModuleCoverageItem(
            module_path="backend/app", total_files=10, tested_files=8,
            coverage_percentage=80.0, status=CoverageStatus.TESTED,
        )
        cov_resp = ProjectCoverageResponse(
            project_id=str(pid), project_name="RepoDefense", total_files=15,
            tested_files_count=9, untested_files_count=6, file_coverage_percentage=60.0,
            evidence_coverage_percentage=75.0, overall_coverage_tier=CoverageTier.SUBSTANTIAL,
            modules=[mod],
        )
        tech_resp = TechAuditReportResponse(
            project_id=str(pid), project_name="RepoDefense",
            total_dependencies_audited=10, flagged_dependencies_count=1,
            critical_count=0, high_count=1, medium_count=0, low_count=0,
            tech_health_score=88,
        )

        cov_mock = AsyncMock(return_value=cov_resp)
        tech_mock = AsyncMock(return_value=tech_resp)
        with (
            patch("app.services.analytics.calculate_project_coverage", cov_mock),
            patch("app.services.analytics.audit_project_technology", tech_mock),
        ):
            report = await build_project_analytics(
                pid, uid, db, fsm_store=fsm, stress_store=stress_store,
                incident_store=incident_store, arch_store=arch_store,
            )

        assert report.project_name == "RepoDefense"
        assert report.total_sessions == 6
        assert report.completed_sessions == 5
        assert report.overall_readiness_pct == 75.0
        assert report.file_coverage_pct == 60.0
        assert report.tech_health_score == 88
        assert len(report.score_trend) == 5
        assert report.language_distribution[0].line_share_pct == 80.0
        modes = {m.mode: m for m in report.mode_breakdown}
        assert modes[DefenseModeKey.CORE_DEFENSE].pass_rate_pct == 100.0
        assert modes[DefenseModeKey.PR_DEFENSE].pass_rate_pct == 0.0
        assert modes[DefenseModeKey.COMMIT_DEFENSE].sessions_completed == 0
        skills = {s.category: s.confidence_pct for s in report.category_skills}
        assert skills["boundary_coherence"] == 80.0

    _run(_impl())


def test_build_project_analytics_graceful_fallback_and_404():
    async def _impl():
        uid, pid = uuid.uuid4(), uuid.uuid4()
        with pytest.raises(HTTPException) as exc:
            await build_project_analytics(pid, uid, _make_fake_db(project=None))
        assert exc.value.status_code == 404

        proj = _proj(pid, uid, name="EmptyRepo", status="pending")
        db_empty = _make_fake_db(project=proj, snapshot_id=None)
        skip_err = AsyncMock(side_effect=RuntimeError("skip"))
        with (
            patch("app.services.analytics.calculate_project_coverage", skip_err),
            patch("app.services.analytics.audit_project_technology", skip_err),
        ):
            report = await build_project_analytics(
                pid, uid, db_empty, fsm_store=DefenseSessionStore(),
                stress_store={}, incident_store={}, arch_store={},
            )
        assert report.overall_readiness_pct is None
        assert report.tech_health_score is None
        assert report.total_sessions == 0

    _run(_impl())


def test_analytics_router_and_workspace_isolation():
    async def _impl():
        uid, pid, other_pid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        user = User(id=uid, email="dev@example.com")
        proj = _proj(pid, uid, name="Alpha")
        db = _make_fake_db(projects=[proj])

        fsm = DefenseSessionStore()
        await _populate_store(fsm, str(pid), str(other_pid))

        ws = await build_workspace_analytics(
            uid, db, fsm_store=fsm, stress_store={}, incident_store={}, arch_store={}
        )
        assert ws.total_projects == 1
        assert ws.analyzed_projects == 1
        assert ws.total_sessions == 3
        assert ws.completed_sessions == 2
        assert ws.avg_readiness_pct == 70.0

        mock_db = AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db
        err_404 = AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))
        try:
            with (
                patch("app.api.v1.analytics.build_workspace_analytics", AsyncMock(return_value=ws)),
                patch("app.api.v1.analytics.build_project_analytics", err_404),
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    r1 = await client.get("/api/v1/analytics/workspace")
                    assert r1.status_code == 200
                    assert r1.json()["avg_readiness_pct"] == 70.0

                    r2 = await client.get(f"/api/v1/analytics/projects/{uuid.uuid4()}")
                    assert r2.status_code == 404
        finally:
            app.dependency_overrides.clear()

    _run(_impl())
