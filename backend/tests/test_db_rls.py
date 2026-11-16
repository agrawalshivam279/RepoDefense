"""Hermetic contract tests ensuring all public tables enforce Supabase RLS lockdown."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import Base

_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "3b7c9d4e2f1a_enable_rls_and_lockdown_public_tables.py"
)

_SKILLS_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "4c8d1e2f3a4b_create_user_skills_and_weaknesses.py"
)


def _load_migration(path: Path, module_name: str):
    assert path.exists(), f"Migration missing: {path}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_rls_migration():
    return _load_migration(_MIGRATION_PATH, "migration_rls_lockdown")


def _load_skills_migration():
    return _load_migration(_SKILLS_MIGRATION_PATH, "migration_skills_lockdown")


def test_rls_migration_lineage_and_full_model_coverage():
    """Verify revision chain and ensure every SQLAlchemy model table is covered by RLS."""
    module = _load_rls_migration()
    assert module.revision == "3b7c9d4e2f1a"
    assert module.down_revision == "2a3f8b9c1d2e"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    declared_tables = set(Base.metadata.tables.keys())
    covered_tables = set(module.APP_TABLES)
    if _SKILLS_MIGRATION_PATH.exists():
        skills_module = _load_skills_migration()
        covered_tables |= set(skills_module.NEW_TABLES)

    missing = declared_tables - covered_tables
    assert not missing, f"SQLAlchemy tables missing RLS lockdown in migration: {sorted(missing)}"


def test_rls_migration_upgrade_and_downgrade_sql():
    """Verify upgrade enables RLS + revokes anon/authenticated and downgrade reverses cleanly."""
    module = _load_rls_migration()
    mock_op = MagicMock()

    with patch.object(module, "op", mock_op):
        module.upgrade()
        up_sql = "\n".join(str(call.args[0]) for call in mock_op.execute.call_args_list)

        for table in module.APP_TABLES:
            assert f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{table}" FROM anon;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{table}" FROM authenticated;' in up_sql

        assert 'ALTER TABLE public."alembic_version" ENABLE ROW LEVEL SECURITY;' in up_sql
        assert 'REVOKE ALL ON TABLE public."alembic_version" FROM anon;' in up_sql
        assert 'REVOKE ALL ON TABLE public."alembic_version" FROM authenticated;' in up_sql
        assert "FORCE ROW LEVEL SECURITY" not in up_sql

        mock_op.reset_mock()
        module.downgrade()
        down_sql = "\n".join(str(call.args[0]) for call in mock_op.execute.call_args_list)

        for table in module.APP_TABLES:
            assert f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;' in down_sql
        assert 'ALTER TABLE public."alembic_version" DISABLE ROW LEVEL SECURITY;' in down_sql


def test_skills_migration_upgrade_and_rls_lockdown_sql():
    """Verify skills migration enables RLS and revokes anon/authenticated table privileges."""
    skills_module = _load_skills_migration()
    assert skills_module.revision == "4c8d1e2f3a4b"
    assert skills_module.down_revision == "3b7c9d4e2f1a"
    mock_op = MagicMock()

    with patch.object(skills_module, "op", mock_op):
        skills_module.upgrade()
        up_sql = "\n".join(str(call.args[0]) for call in mock_op.execute.call_args_list)

        for table in skills_module.NEW_TABLES:
            assert f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{table}" FROM anon;' in up_sql
            assert f'REVOKE ALL ON TABLE public."{table}" FROM authenticated;' in up_sql

        mock_op.reset_mock()
        skills_module.downgrade()
        assert mock_op.drop_table.call_count == 2


def test_rls_migration_rejects_unsafe_table_identifiers():
    """Verify identifier guardrail prevents unsafe DDL interpolation."""
    module = _load_rls_migration()
    with pytest.raises(ValueError, match="Unsafe PostgreSQL table identifier"):
        module._validate_identifier("users; DROP TABLE users;--")
