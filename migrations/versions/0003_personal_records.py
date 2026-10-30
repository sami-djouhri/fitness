"""Add personal_record table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "personal_record",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("exercise_id", sa.Integer, sa.ForeignKey("exercise.id"), nullable=False),
        sa.Column("pr_type", sa.String(20), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("achieved_at", sa.DateTime, nullable=False),
        sa.Column("workout_set_id", sa.Integer, sa.ForeignKey("workout_set.id"), nullable=True),
        sa.UniqueConstraint("exercise_id", "pr_type", name="uq_exercise_pr_type"),
    )


def downgrade() -> None:
    op.drop_table("personal_record")
