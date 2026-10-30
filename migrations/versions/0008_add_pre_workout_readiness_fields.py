"""Add pre-workout readiness fields to workout table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workout",
        sa.Column("fatigue_level", sa.Integer, nullable=True),
    )
    op.add_column(
        "workout",
        sa.Column("sleep_quality", sa.Integer, nullable=True),
    )
    op.add_column(
        "workout",
        sa.Column("motivation", sa.Integer, nullable=True),
    )
    op.add_column(
        "workout",
        sa.Column("pre_notes", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workout", "pre_notes")
    op.drop_column("workout", "motivation")
    op.drop_column("workout", "sleep_quality")
    op.drop_column("workout", "fatigue_level")
