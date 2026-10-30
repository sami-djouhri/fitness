"""Gedaechtnis des Benachrichtigungskanals, je Mandant.

Ersetzt zwei Dateien neben einem Bash-Skript. Die waren nicht
mandantenfaehig: bei zwei Nutzern haette der eine die Erinnerung des anderen
unterdrueckt, weil der Zustand am Wirt hing und nicht am Konto.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anstoss_merker",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_sub", sa.String(128), nullable=False, index=True),
        sa.Column("schluessel", sa.String(200), nullable=False),
        sa.Column("gemeldet_am", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_sub", "schluessel", name="uq_anstoss_owner_schluessel"),
    )


def downgrade() -> None:
    op.drop_table("anstoss_merker")
