"""Create user_skills and candidate_weaknesses tables with RLS lockdown.

Revision ID: 4c8d1e2f3a4b
Revises: 3b7c9d4e2f1a
Create Date: 2026-11-16 19:30:00.000000

"""

import re
from typing import Sequence, Union

from alembic import op
import pgvector
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4c8d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "3b7c9d4e2f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_TABLES: tuple[str, ...] = (
    "user_skills",
    "candidate_weaknesses",
)

_IDENTIFIER_RE = re.compile(r"^[a-z_]+$")


def _validate_identifier(table_name: str) -> str:
    """Validate static PostgreSQL table identifiers before interpolating DDL."""
    if not _IDENTIFIER_RE.fullmatch(table_name):
        raise ValueError(f"Unsafe PostgreSQL table identifier: {table_name!r}")
    return table_name


def _configure_public_table_lockdown(table_name: str, enable: bool) -> None:
    """Toggle RLS and guarded anon/authenticated PostgREST grants on a public table."""
    safe_table = _validate_identifier(table_name)
    rls_action = "ENABLE" if enable else "DISABLE"

    if enable:
        op.execute(f'ALTER TABLE public."{safe_table}" {rls_action} ROW LEVEL SECURITY;')
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."{safe_table}" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."{safe_table}" FROM authenticated;
                END IF;
            END $$;
            """
        )


def upgrade() -> None:
    """Create user_skills and candidate_weaknesses tables and configure RLS."""
    op.create_table(
        "user_skills",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column(
            "proficiency_score", sa.Float(), nullable=False, server_default="50.0"
        ),
        sa.Column(
            "total_evaluations", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "passed_evaluations", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "failed_evaluations", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "category", "topic", name="uq_user_skills_user_category_topic"
        ),
    )
    op.create_index(op.f("ix_user_skills_user_id"), "user_skills", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_skills_category"), "user_skills", ["category"], unique=False)
    op.create_index(op.f("ix_user_skills_topic"), "user_skills", ["topic"], unique=False)
    op.create_index(
        "ix_user_skills_user_proficiency",
        "user_skills",
        ["user_id", "proficiency_score"],
        unique=False,
    )

    op.create_table(
        "candidate_weaknesses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("simulation_mode", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="major"),
        sa.Column("question_prompt", sa.Text(), nullable=False),
        sa.Column("candidate_response", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "topic_embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=384),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_user_id"),
        "candidate_weaknesses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_project_id"),
        "candidate_weaknesses",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_simulation_mode"),
        "candidate_weaknesses",
        ["simulation_mode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_session_id"),
        "candidate_weaknesses",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_category"),
        "candidate_weaknesses",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_topic"),
        "candidate_weaknesses",
        ["topic"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_weaknesses_resolved"),
        "candidate_weaknesses",
        ["resolved"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_weaknesses_user_resolved_severity",
        "candidate_weaknesses",
        ["user_id", "resolved", "severity"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_weaknesses_project_mode",
        "candidate_weaknesses",
        ["project_id", "simulation_mode"],
        unique=False,
    )

    for table in NEW_TABLES:
        _configure_public_table_lockdown(table, enable=True)


def downgrade() -> None:
    """Drop candidate_weaknesses and user_skills tables."""
    op.drop_table("candidate_weaknesses")
    op.drop_table("user_skills")
