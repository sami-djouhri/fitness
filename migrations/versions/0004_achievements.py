"""Add achievement and user_achievement tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "achievement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("category", sa.String(30), nullable=True),
    )

    op.create_table(
        "user_achievement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("achievement_id", sa.Integer, sa.ForeignKey("achievement.id"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_achievement")
    op.drop_table("achievement")
