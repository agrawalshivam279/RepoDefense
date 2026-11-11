"""Enable Row-Level Security and revoke public API grants on all public tables.

RepoDefense routes all application data access through FastAPI using authenticated
SQLAlchemy/asyncpg connections (database owner role bypasses RLS when FORCE is not set).
Enabling default-deny RLS (with zero permissive anon/authenticated policies) and revoking
public role privileges closes Supabase PostgREST exposure (linter 0013_rls_disabled_in_public)
without affecting FastAPI, ARQ workers, or Alembic migrations.

Revision ID: 3b7c9d4e2f1a
Revises: 2a3f8b9c1d2e
Create Date: 2026-11-11 15:40:00.000000

"""

import re
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b7c9d4e2f1a"
down_revision: Union[str, Sequence[str], None] = "2a3f8b9c1d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_TABLES: tuple[str, ...] = (
    "users",
    "projects",
    "dependencies",
    "evidence",
    "repository_snapshots",
    "analyzed_files",
    "code_symbols",
    "code_embeddings",
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
            END
            $$;
            """
        )
    else:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    GRANT ALL ON TABLE public."{safe_table}" TO anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    GRANT ALL ON TABLE public."{safe_table}" TO authenticated;
                END IF;
            END
            $$;
            """
        )
        op.execute(f'ALTER TABLE public."{safe_table}" {rls_action} ROW LEVEL SECURITY;')


def _configure_alembic_version_lockdown(enable: bool) -> None:
    """Conditionally toggle RLS and public API role grants on public.alembic_version."""
    if enable:
        op.execute(
            """
            DO $$
            BEGIN
                IF to_regclass('public.alembic_version') IS NOT NULL THEN
                    ALTER TABLE public."alembic_version" ENABLE ROW LEVEL SECURITY;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        REVOKE ALL ON TABLE public."alembic_version" FROM anon;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        REVOKE ALL ON TABLE public."alembic_version" FROM authenticated;
                    END IF;
                END IF;
            END
            $$;
            """
        )
    else:
        op.execute(
            """
            DO $$
            BEGIN
                IF to_regclass('public.alembic_version') IS NOT NULL THEN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        GRANT ALL ON TABLE public."alembic_version" TO anon;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        GRANT ALL ON TABLE public."alembic_version" TO authenticated;
                    END IF;
                    ALTER TABLE public."alembic_version" DISABLE ROW LEVEL SECURITY;
                END IF;
            END
            $$;
            """
        )


def upgrade() -> None:
    """Lock down all public schema tables against unauthorized Supabase PostgREST access."""
    for table_name in APP_TABLES:
        _configure_public_table_lockdown(table_name, enable=True)
    _configure_alembic_version_lockdown(enable=True)


def downgrade() -> None:
    """Revert public schema RLS and PostgREST role grant restrictions."""
    _configure_alembic_version_lockdown(enable=False)
    for table_name in reversed(APP_TABLES):
        _configure_public_table_lockdown(table_name, enable=False)
