"""Add Phase 2 performance composite indexes on dependencies, evidence, files, and symbols.

Revision ID: 2a3f8b9c1d2e
Revises: 16d48d0545e1
Create Date: 2026-11-08 00:35:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3f8b9c1d2e"
down_revision: Union[str, Sequence[str], None] = "16d48d0545e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 2 performance composite indexes."""
    op.create_index(
        "ix_dependencies_project_name",
        "dependencies",
        ["project_id", "name"],
        unique=False,
    )
    op.create_index(
        "ix_analyzed_files_snapshot_path",
        "analyzed_files",
        ["snapshot_id", "path"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_project_type",
        "evidence",
        ["project_id", "evidence_type"],
        unique=False,
    )
    op.create_index(
        "ix_code_symbols_file_symbol_type",
        "code_symbols",
        ["file_id", "symbol_type"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Phase 2 performance composite indexes."""
    op.drop_index("ix_code_symbols_file_symbol_type", table_name="code_symbols")
    op.drop_index("ix_evidence_project_type", table_name="evidence")
    op.drop_index("ix_analyzed_files_snapshot_path", table_name="analyzed_files")
    op.drop_index("ix_dependencies_project_name", table_name="dependencies")
