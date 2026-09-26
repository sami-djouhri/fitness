"""Feinere Uebungsdaten, Nutzerprofil, Tagesschritte.

Drei Dinge auf einmal, weil sie zusammengehoeren: die App soll aufhoeren,
Uebungen vorzuschlagen, deren Geraete es nicht gibt, und dafuer braucht sie
(1) an der Uebung, was sie braucht, (2) am Nutzer, was er hat, und (3) einen
Ort fuer die Schritte, damit das Aktivitaetsniveau nicht nur aus dem Training
kommt.

★ Die Spalte ``kg_anteil`` ist die wichtigste hier. Ohne sie hat jede
Koerpergewichtsuebung das Volumen null, weil ``weight_kg`` leer bleibt, und
die gesamte Fortschrittsanzeige eines Heimtrainers ist eine Nulllinie.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEUE_SPALTEN = [
    ("muskel_anteile_json", sa.Text(), True, None),
    ("benoetigt_json", sa.Text(), True, None),
    ("muster", sa.String(40), True, None),
    ("kg_anteil", sa.Float(), False, "0"),
    ("griff", sa.String(20), True, None),
    ("reihe", sa.String(40), True, None),
    ("stufe", sa.Integer(), False, "0"),
    ("einseitig", sa.Boolean(), False, "0"),
    ("ist_zeit", sa.Boolean(), False, "0"),
    ("wdh_min", sa.Integer(), False, "8"),
    ("wdh_max", sa.Integer(), False, "12"),
    ("pause_s", sa.Integer(), False, "90"),
    ("ausfuehrung", sa.Text(), True, None),
    ("fehler", sa.Text(), True, None),
]


def upgrade() -> None:
    with op.batch_alter_table("exercise") as batch:
        for name, typ, nullable, default in NEUE_SPALTEN:
            batch.add_column(sa.Column(
                name, typ, nullable=nullable,
                server_default=sa.text(default) if default is not None else None,
            ))
    op.create_index("ix_exercise_reihe", "exercise", ["reihe"])

    op.create_table(
        "nutzerprofil",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_sub", sa.String(128), nullable=False, index=True),
        sa.Column("geraete_json", sa.Text, nullable=True),
        sa.Column("eingerichtet", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("erfahrung", sa.String(20), nullable=False, server_default="einsteiger"),
        sa.Column("ziel", sa.String(20), nullable=False, server_default="hypertrophie"),
        sa.Column("trainingstage_pro_woche", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column("gewichtsschritt_kg", sa.Float, nullable=False, server_default=sa.text("2.5")),
        sa.Column("kurzhantel_max_kg", sa.Float, nullable=True),
        sa.Column("koerpergewicht_kg", sa.Float, nullable=True),
        sa.Column("koerpergroesse_cm", sa.Float, nullable=True),
        sa.Column("geburtsjahr", sa.Integer, nullable=True),
        sa.Column("geschlecht", sa.String(15), nullable=False, server_default="keine_angabe"),
        sa.Column("einschraenkungen_json", sa.Text, nullable=True),
        sa.Column("aktualisiert_am", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_sub", name="uq_nutzerprofil_owner"),
    )

    op.create_table(
        "tagesschritte",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_sub", sa.String(128), nullable=False, index=True),
        sa.Column("datum", sa.Date, nullable=False, index=True),
        sa.Column("schritte", sa.Integer, nullable=False),
        sa.Column("distanz_m", sa.Float, nullable=True),
        sa.Column("aktive_kcal", sa.Float, nullable=True),
        sa.Column("quelle", sa.String(20), nullable=False, server_default="manuell"),
        sa.Column("gemeldet_am", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_sub", "datum", name="uq_schritte_owner_datum"),
    )


def downgrade() -> None:
    op.drop_table("tagesschritte")
    op.drop_table("nutzerprofil")
    op.drop_index("ix_exercise_reihe", table_name="exercise")
    with op.batch_alter_table("exercise") as batch:
        for name, _typ, _nullable, _default in reversed(NEUE_SPALTEN):
            batch.drop_column(name)
