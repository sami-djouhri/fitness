"""multi-tenant: owner_sub auf Tenant-Tabellen + Composite-Uniques

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-04

exercise + achievement bleiben GLOBAL (geteilte Kataloge, kein owner_sub).
Tenant-Tabellen bekommen owner_sub (server_default=Owner backfillt Alt-Daten).
body_metric.date (unbenannt) und personal_record(exercise_id,pr_type) werden zu
(owner_sub, ...)-Composites via batch_alter_table (SQLite-Rebuild).
"""

import os

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# Owner aller Alt-Daten. Kommt aus der Umgebung (DEFAULT_OWNER_SUB), nicht mehr
# aus dem Quelltext: die Kennung gehoert einem konkreten Menschen, und dieses
# Repo soll veroeffentlicht werden koennen (2026-09-05).
#
# Leer ist unbedenklich. Der Wert dient als server_default beim Hinzufuegen der
# NOT-NULL-Spalte, also der Bestandsuebernahme. Bei einer frischen Installation
# gibt es keinen Bestand, und neue Zeilen stempelt ohnehin das ORM
# (app/tenant.py, before_flush), nicht dieser Vorgabewert.
#
# ⚠️ Wer diese Migration auf einer BESTEHENDEN Datenbank zum ersten Mal faehrt,
# sollte DEFAULT_OWNER_SUB setzen, sonst gehoeren die Alt-Daten niemandem.
OWNER = os.environ.get("DEFAULT_OWNER_SUB", "")
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}

# Tenant-Tabellen ohne Unique-Aenderung: nur owner_sub + Index.
SIMPLE = ("plan", "plan_day", "plan_exercise", "workout", "workout_set", "user_achievement")


def upgrade() -> None:
    for tbl in SIMPLE:
        with op.batch_alter_table(tbl) as b:
            b.add_column(sa.Column("owner_sub", sa.String(128), nullable=False, server_default=OWNER))
            b.create_index(f"ix_{tbl}_owner_sub", ["owner_sub"])

    # body_metric: unbenannte UNIQUE(date) -> (owner_sub, date)
    with op.batch_alter_table("body_metric", naming_convention=NAMING) as b:
        b.add_column(sa.Column("owner_sub", sa.String(128), nullable=False, server_default=OWNER))
        b.drop_constraint("uq_body_metric_date", type_="unique")
        b.create_unique_constraint("uq_body_metric_owner_date", ["owner_sub", "date"])
        b.create_index("ix_body_metric_owner_sub", ["owner_sub"])

    # personal_record: benannte UNIQUE(exercise_id, pr_type) -> (owner_sub, ...)
    with op.batch_alter_table("personal_record") as b:
        b.add_column(sa.Column("owner_sub", sa.String(128), nullable=False, server_default=OWNER))
        b.drop_constraint("uq_exercise_pr_type", type_="unique")
        b.create_unique_constraint(
            "uq_owner_exercise_pr_type", ["owner_sub", "exercise_id", "pr_type"]
        )
        b.create_index("ix_personal_record_owner_sub", ["owner_sub"])


def downgrade() -> None:
    with op.batch_alter_table("personal_record") as b:
        b.drop_constraint("uq_owner_exercise_pr_type", type_="unique")
        b.create_unique_constraint("uq_exercise_pr_type", ["exercise_id", "pr_type"])
        b.drop_index("ix_personal_record_owner_sub")
        b.drop_column("owner_sub")

    with op.batch_alter_table("body_metric", naming_convention=NAMING) as b:
        b.drop_constraint("uq_body_metric_owner_date", type_="unique")
        b.create_unique_constraint("uq_body_metric_date", ["date"])
        b.drop_index("ix_body_metric_owner_sub")
        b.drop_column("owner_sub")

    for tbl in reversed(SIMPLE):
        with op.batch_alter_table(tbl) as b:
            b.drop_index(f"ix_{tbl}_owner_sub")
            b.drop_column("owner_sub")
