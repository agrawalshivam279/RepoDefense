"""Add github_username column and index to users table.

Revision ID: 6f1a2b3c4d5e
Revises: 5d9e2f3a4b5c
Create Date: 2026-11-19 21:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "5d9e2f3a4b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable github_username column and index to users table."""
    op.add_column("users", sa.Column("github_username", sa.String(255), nullable=True))
    op.create_index("ix_users_github_username", "users", ["github_username"], unique=False)


def downgrade() -> None:
    """Drop index and column github_username from users table."""
    op.drop_index("ix_users_github_username", table_name="users")
    op.drop_column("users", "github_username")
