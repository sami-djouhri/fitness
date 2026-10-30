"""Initial schema.

Revision ID: 0001
Revises:
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercise",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("equipment", sa.String(50), nullable=False),
        sa.Column("primary_muscles_json", sa.Text, nullable=True),
        sa.Column("is_compound", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "plan",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "plan_day",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("plan.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=True),
        sa.Column("sort_order", sa.Integer, default=0),
    )

    op.create_table(
        "plan_exercise",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_day_id", sa.Integer, sa.ForeignKey("plan_day.id"), nullable=False),
        sa.Column("exercise_id", sa.Integer, sa.ForeignKey("exercise.id"), nullable=False),
        sa.Column("sort_order", sa.Integer, default=0),
        sa.Column("target_sets", sa.Integer, default=3),
        sa.Column("target_reps_min", sa.Integer, default=8),
        sa.Column("target_reps_max", sa.Integer, default=12),
        sa.Column("target_rpe", sa.Float, nullable=True),
        sa.Column("rest_seconds", sa.Integer, default=90),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "workout",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_day_id", sa.Integer, sa.ForeignKey("plan_day.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
    )

    op.create_table(
        "workout_set",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workout_id", sa.Integer, sa.ForeignKey("workout.id"), nullable=False),
        sa.Column("exercise_id", sa.Integer, sa.ForeignKey("exercise.id"), nullable=False),
        sa.Column("set_number", sa.Integer, nullable=False),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("reps", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("distance_meters", sa.Float, nullable=True),
        sa.Column("rpe", sa.Float, nullable=True),
        sa.Column("is_warmup", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "body_metric",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("weight_kg", sa.Float, nullable=False),
        sa.Column("body_fat_pct", sa.Float, nullable=True),
        sa.Column("waist_cm", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("body_metric")
    op.drop_table("workout_set")
    op.drop_table("workout")
    op.drop_table("plan_exercise")
    op.drop_table("plan_day")
    op.drop_table("plan")
    op.drop_table("exercise")
