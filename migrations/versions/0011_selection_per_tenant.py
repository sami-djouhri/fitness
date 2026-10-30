"""Uebungsauswahl je Mandant, Eigentuemer je Katalogeintrag.

Zwei Loecher derselben Art: ``exercise`` ist ein bewusst GETEILTER Katalog
(app/tenant.py), trug aber Zustand, der einer einzelnen Person gehoert.

1. ``is_selected`` hiess "habe ich in meinem Studio". Wer abwaehlte, waehlte
   allen ab. Wandert nach ``exercise_selection``; kein Eintrag heisst
   ausgewaehlt, deshalb muss fuer den Bestand nichts geschrieben werden
   (gemessen: alle 67 Eintraege standen auf ausgewaehlt).
2. Anlegen, Aendern und Loeschen im Katalog war fuer jeden offen, ohne
   Eigentuemer und ohne Pruefung auf Verwendung. In der oeffentlichen Demo
   haette ein Besucher Eintraege loeschen koennen, die in fremden Plaenen und
   Workouts haengen. ``created_by_sub`` macht den Urheber kenntlich: NULL sind
   die Eintraege aus dem Seed, die niemand aendert.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercise_selection",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_sub", sa.String(64), nullable=False, index=True),
        sa.Column(
            "exercise_id", sa.Integer,
            sa.ForeignKey("exercise.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("is_selected", sa.Boolean, nullable=False, server_default="1"),
        sa.UniqueConstraint("owner_sub", "exercise_id", name="uq_selection_owner_exercise"),
    )
    op.add_column("exercise", sa.Column("created_by_sub", sa.String(64), nullable=True))
    op.create_index("ix_exercise_created_by_sub", "exercise", ["created_by_sub"])

    # Abgewaehltes aus dem Bestand dem Mandanten zuschreiben, der Plaene hat.
    # Ist der Bestand einstimmig ausgewaehlt, schreibt das nichts: genau so
    # war es hier, die Abfrage bleibt fuer andere Installationen stehen.
    verbindung = op.get_bind()
    verbindung.execute(sa.text("""
        INSERT INTO exercise_selection (owner_sub, exercise_id, is_selected)
        SELECT (SELECT owner_sub FROM plan ORDER BY id LIMIT 1), id, 0
        FROM exercise
        WHERE is_selected = 0
          AND (SELECT COUNT(*) FROM plan) > 0
    """))


def downgrade() -> None:
    op.drop_index("ix_exercise_created_by_sub", table_name="exercise")
    op.drop_column("exercise", "created_by_sub")
    op.drop_table("exercise_selection")
