"""Koerpermasse: 13 Umfaenge je Tag, eigene Tabelle (Entscheid 2026-11-07).

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "koerpermass",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_sub", sa.String(128), nullable=False, index=True),
        sa.Column("datum", sa.Date, nullable=False, index=True),
        sa.Column("mass", sa.String(30), nullable=False),
        sa.Column("wert_cm", sa.Float, nullable=False),
        sa.UniqueConstraint("owner_sub", "datum", "mass", name="uq_koerpermass_owner_datum_mass"),
    )


def downgrade() -> None:
    op.drop_table("koerpermass")
