"""Add is_selected column to exercise table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercise",
        sa.Column("is_selected", sa.Boolean, server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("exercise", "is_selected")
