"""Add indexes for query performance.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_workout_started_at", "workout", ["started_at"])
    op.create_index("idx_workout_set_workout_id", "workout_set", ["workout_id"])
    op.create_index("idx_workout_set_exercise_id", "workout_set", ["exercise_id"])
    # body_metric.date already has a unique constraint (implicit index): skipped
    op.create_index("idx_plan_day_plan_id", "plan_day", ["plan_id"])
    op.create_index("idx_plan_exercise_plan_day_id", "plan_exercise", ["plan_day_id"])
    op.create_index("idx_plan_exercise_exercise_id", "plan_exercise", ["exercise_id"])


def downgrade() -> None:
    op.drop_index("idx_plan_exercise_exercise_id")
    op.drop_index("idx_plan_exercise_plan_day_id")
    op.drop_index("idx_plan_day_plan_id")
    op.drop_index("idx_workout_set_exercise_id")
    op.drop_index("idx_workout_set_workout_id")
    op.drop_index("idx_workout_started_at")
