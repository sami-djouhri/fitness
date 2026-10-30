"""Abhak-Zustand je Satz (geplant gegen gemacht).

Seit die Session aus dem Trainingstag vorbefuellt wird, existiert ein Satz auch
dann schon, wenn er noch nicht ausgefuehrt ist. Ohne diese Unterscheidung
zaehlten Volumen, Rekorde und Auszeichnungen die Vorgabe als Leistung.

``server_default="1"`` fuer den Bestand: ein vor dieser Migration eingetragener
Satz war immer ein gemachter Satz.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workout_set",
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="1"),
    )
    op.add_column(
        "workout_set",
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    # Teilindex waere schoener, SQLite kann ihn aber nur ueber rohes SQL.
    # Der zusammengesetzte Index traegt die Abfragen des Fortschritts, die
    # jetzt durchgehend auf is_completed einschraenken.
    op.create_index(
        "ix_workout_set_completed",
        "workout_set",
        ["is_completed", "exercise_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workout_set_completed", table_name="workout_set")
    op.drop_column("workout_set", "completed_at")
    op.drop_column("workout_set", "is_completed")
