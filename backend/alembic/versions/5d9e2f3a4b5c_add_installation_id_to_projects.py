"""Add installation_id column and index to projects table.

Revision ID: 5d9e2f3a4b5c
Revises: 4c8d1e2f3a4b
Create Date: 2026-11-19 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d9e2f3a4b5c"
down_revision: Union[str, Sequence[str], None] = "4c8d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable installation_id column and index to projects table."""
    op.add_column("projects", sa.Column("installation_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_projects_installation_id", "projects", ["installation_id"], unique=False)


def downgrade() -> None:
    """Drop index and column installation_id from projects table."""
    op.drop_index("ix_projects_installation_id", table_name="projects")
    op.drop_column("projects", "installation_id")
