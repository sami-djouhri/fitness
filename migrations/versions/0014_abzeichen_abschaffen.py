"""Abzeichen abschaffen: ``achievement`` und ``user_achievement`` fallen.

Entscheid 2026-10-24. Gemessen waren 18 Definitionen aktiv und zwei
davon erreicht, angezeigt wurde nichts: es gab keine Oberflaeche dafuer, nur
einen Aufruf von ``POST /achievements/check`` am Ende jeder Einheit, dessen
Ergebnis niemand las.

Die Tabellen werden wirklich entfernt und nicht nur nicht mehr benutzt.
Eine Tabelle ohne Code dahinter ist schlimmer als keine: sie steht im
Datenexport, im Loeschplan nach Artikel 17 und in jedem Schema-Abgleich, und
beim naechsten Lesen sieht sie aus wie ein Teil, das jemand vergessen hat
anzuschliessen.

⚠️ ``user_achievement`` traegt Nutzerdaten (zwei Zeilen zum Zeitpunkt der
Migration). Sie sind ableitbar: jedes Abzeichen wurde aus Einheiten und
Saetzen gerechnet, die unberuehrt bleiben. Der Rueckweg unten legt beide
Tabellen wieder an, kann die erreichten Abzeichen aber nicht
zurueckbringen. Das ist die Folge des Entscheids und keine Nachlaessigkeit.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kind zuerst: ``user_achievement`` haelt den Fremdschluessel.
    for tabelle in ("user_achievement", "achievement"):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {tabelle}"))


def downgrade() -> None:
    op.create_table(
        "achievement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=10), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=True),
    )
    op.create_table(
        "user_achievement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_sub", sa.String(length=128), nullable=False, index=True),
        sa.Column("achievement_id", sa.Integer(),
                  sa.ForeignKey("achievement.id"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), server_default=sa.func.now()),
    )
