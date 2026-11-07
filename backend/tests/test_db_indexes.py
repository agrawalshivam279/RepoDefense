"""Hermetic unit tests for Phase 2 database performance indexes and Alembic migration."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models.analysis import AnalyzedFile, CodeSymbol, Dependency, Evidence


def _extract_indexes(table):
    return {idx.name: [c.name for c in idx.columns] for idx in table.indexes}


def test_analyzed_file_composite_index_metadata():
    """Verify AnalyzedFile declares composite index on snapshot_id and path."""
    indexes = _extract_indexes(AnalyzedFile.__table__)
    assert "ix_analyzed_files_snapshot_path" in indexes
    assert indexes["ix_analyzed_files_snapshot_path"] == ["snapshot_id", "path"]


def test_code_symbol_composite_index_metadata():
    """Verify CodeSymbol declares composite index on file_id and symbol_type."""
    indexes = _extract_indexes(CodeSymbol.__table__)
    assert "ix_code_symbols_file_symbol_type" in indexes
    assert indexes["ix_code_symbols_file_symbol_type"] == ["file_id", "symbol_type"]


def test_dependency_composite_index_metadata():
    """Verify Dependency declares composite index on project_id and name."""
    indexes = _extract_indexes(Dependency.__table__)
    assert "ix_dependencies_project_name" in indexes
    assert indexes["ix_dependencies_project_name"] == ["project_id", "name"]


def test_evidence_composite_index_metadata():
    """Verify Evidence declares composite index on project_id and evidence_type."""
    indexes = _extract_indexes(Evidence.__table__)
    assert "ix_evidence_project_type" in indexes
    assert indexes["ix_evidence_project_type"] == ["project_id", "evidence_type"]


def test_migration_phase2_indexes_module_attributes():
    """Verify Alembic migration revision identifiers and lineage."""
    migration_file = Path("backend/alembic/versions/2a3f8b9c1d2e_add_phase2_performance_indexes.py")
    assert migration_file.exists(), f"Migration file missing: {migration_file}"

    spec = importlib.util.spec_from_file_location("migration_phase2", str(migration_file))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "2a3f8b9c1d2e"
    assert module.down_revision == "16d48d0545e1"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_migration_upgrade_and_downgrade_operations():
    """Verify migration upgrade and downgrade invoke Alembic op methods correctly."""
    migration_file = Path("backend/alembic/versions/2a3f8b9c1d2e_add_phase2_performance_indexes.py")
    spec = importlib.util.spec_from_file_location("migration_phase2_ops", str(migration_file))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    mock_op = MagicMock()
    with patch.object(module, "op", mock_op):
        # Execute upgrade
        module.upgrade()
        assert mock_op.create_index.call_count == 4
        created_index_names = [call.args[0] for call in mock_op.create_index.call_args_list]
        assert "ix_dependencies_project_name" in created_index_names
        assert "ix_analyzed_files_snapshot_path" in created_index_names
        assert "ix_evidence_project_type" in created_index_names
        assert "ix_code_symbols_file_symbol_type" in created_index_names

        # Execute downgrade (reversible verification)
        mock_op.reset_mock()
        module.downgrade()
        assert mock_op.drop_index.call_count == 4
        dropped_index_names = [call.args[0] for call in mock_op.drop_index.call_args_list]
        assert "ix_code_symbols_file_symbol_type" in dropped_index_names
        assert "ix_evidence_project_type" in dropped_index_names
        assert "ix_analyzed_files_snapshot_path" in dropped_index_names
        assert "ix_dependencies_project_name" in dropped_index_names


def test_indexed_queries_construction():
    """Verify SQLAlchemy select statements targeting indexed columns compile cleanly."""
    stmt_dep = select(Dependency.name, Dependency.version).where(
        Dependency.project_id != None,  # noqa: E711
        Dependency.name == "fastapi",
    )
    assert "dependencies.project_id" in str(stmt_dep)
    assert "dependencies.name" in str(stmt_dep)

    stmt_ev = select(Evidence.id).where(
        Evidence.project_id != None,  # noqa: E711
        Evidence.evidence_type == "architecture",
    )
    assert "evidence.project_id" in str(stmt_ev)
    assert "evidence.evidence_type" in str(stmt_ev)
