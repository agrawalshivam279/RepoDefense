"""create_initial_schema

Revision ID: 16d48d0545e1
Revises:
Create Date: 2026-10-26 16:53:46.458073

"""
from typing import Sequence, Union

import pgvector
import pgvector.sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "16d48d0545e1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"], unique=False)

    op.create_table(
        "dependencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("is_dev", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dependencies_name"), "dependencies", ["name"], unique=False)
    op.create_index(
        op.f("ix_dependencies_project_id"), "dependencies", ["project_id"], unique=False
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_evidence_type"), "evidence", ["evidence_type"], unique=False)
    op.create_index(op.f("ix_evidence_project_id"), "evidence", ["project_id"], unique=False)

    op.create_table(
        "repository_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("commit_hash", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repository_snapshots_project_id"),
        "repository_snapshots",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "analyzed_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("total_lines", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["repository_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyzed_files_path"), "analyzed_files", ["path"], unique=False)
    op.create_index(
        op.f("ix_analyzed_files_snapshot_id"), "analyzed_files", ["snapshot_id"], unique=False
    )

    op.create_table(
        "code_symbols",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("symbol_type", sa.String(length=50), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["analyzed_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_symbols_file_id"), "code_symbols", ["file_id"], unique=False)
    op.create_index(op.f("ix_code_symbols_name"), "code_symbols", ["name"], unique=False)
    op.create_index(
        op.f("ix_code_symbols_symbol_type"), "code_symbols", ["symbol_type"], unique=False
    )

    op.create_table(
        "code_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("symbol_id", sa.UUID(), nullable=True),
        sa.Column("chunk_content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["analyzed_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["code_symbols.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_code_embeddings_hnsw",
        "code_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_code_embeddings_file_id"), "code_embeddings", ["file_id"], unique=False
    )
    op.create_index(
        op.f("ix_code_embeddings_symbol_id"), "code_embeddings", ["symbol_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_code_embeddings_symbol_id"), table_name="code_embeddings")
    op.drop_index(op.f("ix_code_embeddings_file_id"), table_name="code_embeddings")
    op.drop_index(
        "idx_code_embeddings_hnsw",
        table_name="code_embeddings",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("code_embeddings")
    op.drop_index(op.f("ix_code_symbols_symbol_type"), table_name="code_symbols")
    op.drop_index(op.f("ix_code_symbols_name"), table_name="code_symbols")
    op.drop_index(op.f("ix_code_symbols_file_id"), table_name="code_symbols")
    op.drop_table("code_symbols")
    op.drop_index(op.f("ix_analyzed_files_snapshot_id"), table_name="analyzed_files")
    op.drop_index(op.f("ix_analyzed_files_path"), table_name="analyzed_files")
    op.drop_table("analyzed_files")
    op.drop_index(op.f("ix_repository_snapshots_project_id"), table_name="repository_snapshots")
    op.drop_table("repository_snapshots")
    op.drop_index(op.f("ix_evidence_project_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_evidence_type"), table_name="evidence")
    op.drop_table("evidence")
    op.drop_index(op.f("ix_dependencies_project_id"), table_name="dependencies")
    op.drop_index(op.f("ix_dependencies_name"), table_name="dependencies")
    op.drop_table("dependencies")
    op.drop_index(op.f("ix_projects_user_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
