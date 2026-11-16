"""Unit and schema contract tests for candidate skill and weakness tracking models."""

import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.project import Project, User
from app.models.skill import CandidateWeakness, UserSkill
from app.schemas.skill import (
    CandidateWeaknessCreate,
    CandidateWeaknessResponse,
    CandidateWeaknessUpdate,
    SkillCategory,
    UserSkillBase,
    UserSkillCreate,
    UserSkillResponse,
    UserSkillsOverviewResponse,
    UserSkillUpdate,
    WeaknessSeverity,
)

_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "4c8d1e2f3a4b_create_user_skills_and_weaknesses.py"
)


def _load_migration():
    assert _MIGRATION_PATH.exists(), f"Migration file missing: {_MIGRATION_PATH}"
    spec = importlib.util.spec_from_file_location("skills_migration", str(_MIGRATION_PATH))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_user_skill_schema_validations():
    """Verify UserSkillBase and UserSkillCreate schema constraints and score clamping."""
    skill = UserSkillBase(
        category="architecture",
        topic="connection_pooling",
        proficiency_score=78.5,
        total_evaluations=4,
        passed_evaluations=3,
        failed_evaluations=1,
    )
    assert skill.proficiency_score == 78.5
    assert skill.passed_evaluations == 3

    # Clamped bounds: score must be between 0.0 and 100.0
    for bad_score in [-5.0, 105.0]:
        with pytest.raises(ValidationError):
            UserSkillBase(category="auth", topic="jwt", proficiency_score=bad_score)

    # String length bounds
    for bad_cat, bad_top in [("a" * 65, "jwt"), ("auth", "b" * 129)]:
        with pytest.raises(ValidationError):
            UserSkillBase(category=bad_cat, topic=bad_top)

    # Valid creation with user_id
    uid = uuid.uuid4()
    create_schema = UserSkillCreate(
        user_id=uid,
        category="scalability",
        topic="cache_invalidation",
    )
    assert create_schema.user_id == uid
    assert create_schema.proficiency_score == 50.0  # default score


def test_user_skill_update_and_response_schema():
    """Verify partial updates and serialization to UserSkillResponse."""
    update = UserSkillUpdate(proficiency_score=85.0, passed=True)
    assert update.proficiency_score == 85.0
    assert update.passed is True

    uid = uuid.uuid4()
    skill_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    res = UserSkillResponse(
        id=skill_id,
        user_id=uid,
        category="security",
        topic="stateless_tokens",
        proficiency_score=90.0,
        total_evaluations=5,
        passed_evaluations=5,
        failed_evaluations=0,
        created_at=now,
        updated_at=now,
    )
    assert res.id == skill_id
    assert res.proficiency_score == 90.0


def test_candidate_weakness_schema_validations():
    """Verify CandidateWeaknessCreate, Update, and Response schemas."""
    uid = uuid.uuid4()
    pid = uuid.uuid4()

    weakness = CandidateWeaknessCreate(
        user_id=uid,
        project_id=pid,
        simulation_mode="stress_test",
        category=SkillCategory.SCALABILITY.value,
        topic="database_indexing",
        severity=WeaknessSeverity.CRITICAL,
        question_prompt="What happens if the table has 10M rows without an index?",
        candidate_response="A table scan will occur.",
        feedback="Missing mention of B-tree vs BRIN indexes and connection queue starvation.",
    )
    assert weakness.severity == WeaknessSeverity.CRITICAL
    assert weakness.simulation_mode == "stress_test"

    # Default severity is MAJOR
    default_w = CandidateWeaknessCreate(
        user_id=uid,
        project_id=pid,
        simulation_mode="arch_defense",
        category="tradeoffs",
        topic="event_driven",
        question_prompt="Why use polling instead of webhooks?",
        feedback="Polling increases edge latency.",
    )
    assert default_w.severity == WeaknessSeverity.MAJOR

    # String length bounds
    base_kwargs = {
        "user_id": uid,
        "project_id": pid,
        "question_prompt": "q",
        "feedback": "f",
    }
    bad_fields = [
        {"simulation_mode": "m" * 33, "category": "c", "topic": "t"},
        {"simulation_mode": "c", "category": "c" * 65, "topic": "t"},
        {"simulation_mode": "c", "category": "c", "topic": "t" * 129},
        {"simulation_mode": "c", "category": "c", "topic": "t", "session_id": "s" * 65},
    ]
    for bf in bad_fields:
        with pytest.raises(ValidationError):
            CandidateWeaknessCreate(**base_kwargs, **bf)

    # Embedding dimension validation: exactly 384 or None
    for bad_emb in [[], [0.1] * 383, [0.1] * 385]:
        with pytest.raises(ValidationError):
            CandidateWeaknessCreate(
                **base_kwargs, simulation_mode="c", category="c", topic="t", topic_embedding=bad_emb
            )

    valid_emb = CandidateWeaknessCreate(
        **base_kwargs, simulation_mode="c", category="c", topic="t", topic_embedding=[0.1] * 384
    )
    assert len(valid_emb.topic_embedding) == 384

    # Update schema
    resolved_time = datetime.now(timezone.utc)
    update = CandidateWeaknessUpdate(resolved=True, resolved_at=resolved_time)
    assert update.resolved is True
    assert update.resolved_at == resolved_time

    # Response schema
    wid = uuid.uuid4()
    res = CandidateWeaknessResponse(
        id=wid,
        user_id=uid,
        project_id=pid,
        simulation_mode="core_defense",
        category="reliability",
        topic="circuit_breaker",
        severity=WeaknessSeverity.MAJOR,
        question_prompt="How do you prevent cascading failure?",
        feedback="Implement fallback responses and exponential backoff.",
        resolved=False,
        has_embedding=False,
        created_at=resolved_time,
        updated_at=resolved_time,
    )
    assert res.id == wid
    assert res.resolved is False


def test_user_skills_overview_response():
    """Verify aggregate overview serialization across skills and weaknesses."""
    uid = uuid.uuid4()
    overview = UserSkillsOverviewResponse(
        user_id=uid,
        total_skills_tracked=3,
        avg_proficiency_pct=72.5,
        weak_skills_count=1,
        strong_skills_count=2,
        unresolved_weaknesses_count=1,
        resolved_weaknesses_count=0,
    )
    assert overview.user_id == uid
    assert overview.total_skills_tracked == 3
    assert overview.avg_proficiency_pct == 72.5


def test_sqlalchemy_user_skill_model_contracts():
    """Verify SQLAlchemy 2.0 column types, table args, and default values for UserSkill."""
    assert UserSkill.__tablename__ == "user_skills"

    # Column presence and types
    cols = {c.name: c for c in UserSkill.__table__.columns}
    for col in [
        "id", "user_id", "category", "topic", "proficiency_score",
        "total_evaluations", "passed_evaluations", "failed_evaluations",
        "created_at", "updated_at",
    ]:
        assert col in cols

    # Unique constraint check
    uq_names = [c.name for c in UserSkill.__table__.constraints if hasattr(c, "columns")]
    assert "uq_user_skills_user_category_topic" in uq_names

    # Relationship check on User
    assert hasattr(User, "skills")
    assert hasattr(User, "weaknesses")


def test_sqlalchemy_candidate_weakness_model_contracts():
    """Verify SQLAlchemy 2.0 column types, table args, and foreign keys for CandidateWeakness."""
    assert CandidateWeakness.__tablename__ == "candidate_weaknesses"

    cols = {c.name: c for c in CandidateWeakness.__table__.columns}
    for col in [
        "id", "user_id", "project_id", "simulation_mode", "session_id",
        "category", "topic", "severity", "question_prompt",
        "candidate_response", "feedback", "resolved", "resolved_at",
        "topic_embedding",
    ]:
        assert col in cols

    # Foreign keys and relationships
    fk_targets = [str(fk.target_fullname) for fk in CandidateWeakness.__table__.foreign_keys]
    assert "users.id" in fk_targets and "projects.id" in fk_targets
    assert hasattr(Project, "weaknesses")

    # has_embedding property check on model and response derivation
    now = datetime.now(timezone.utc)
    w_inst = CandidateWeakness(
        id=uuid.uuid4(), user_id=uuid.uuid4(), project_id=uuid.uuid4(),
        simulation_mode="core", category="scalability", topic="indexing",
        severity="major", question_prompt="q", feedback="f",
        resolved=False, created_at=now, updated_at=now,
    )
    assert w_inst.has_embedding is False
    w_inst.topic_embedding = [0.1] * 384
    assert w_inst.has_embedding is True
    res_from_orm = CandidateWeaknessResponse.model_validate(w_inst)
    assert res_from_orm.has_embedding is True


def test_migration_chain_and_rls_lockdown_contracts():
    """Verify the Alembic migration sets up tables, indexes, and public RLS lockdown."""
    module = _load_migration()
    assert module.revision == "4c8d1e2f3a4b"
    assert module.down_revision == "3b7c9d4e2f1a"
    assert "user_skills" in module.NEW_TABLES
    assert "candidate_weaknesses" in module.NEW_TABLES

    mock_op = MagicMock()
    with patch.object(module, "op", mock_op):
        module.upgrade()
        # Verify tables created
        created_tables = [call.args[0] for call in mock_op.create_table.call_args_list]
        assert "user_skills" in created_tables
        assert "candidate_weaknesses" in created_tables

        # Verify RLS lockdown executed on both new tables
        up_sql = "\n".join(str(call.args[0]) for call in mock_op.execute.call_args_list)
        for t in module.NEW_TABLES:
            assert f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{t}" FROM anon;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{t}" FROM authenticated;' in up_sql

        # Verify downgrade drops tables
        mock_op.reset_mock()
        module.downgrade()
        dropped_tables = [call.args[0] for call in mock_op.drop_table.call_args_list]
        assert "candidate_weaknesses" in dropped_tables
        assert "user_skills" in dropped_tables
