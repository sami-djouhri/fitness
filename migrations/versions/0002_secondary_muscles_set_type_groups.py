"""Add secondary_muscles, set_type, group_id.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercise", sa.Column("secondary_muscles_json", sa.Text, nullable=True))
    op.add_column("workout_set", sa.Column("set_type", sa.String(20), server_default="normal"))
    op.add_column("workout_set", sa.Column("group_id", sa.String(36), nullable=True))

    # Migrate existing warmup sets: set_type='warmup' where is_warmup=1
    op.execute("UPDATE workout_set SET set_type = 'warmup' WHERE is_warmup = 1")


def downgrade() -> None:
    op.drop_column("workout_set", "group_id")
    op.drop_column("workout_set", "set_type")
    op.drop_column("exercise", "secondary_muscles_json")
