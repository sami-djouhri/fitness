"""Seed stretching exercises (Dehnung).

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-01
"""
from typing import Sequence, Union

import json
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STRETCHES = [
    {"name": "Brustdehnung an der Wand", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Brust"], "secondary": ["Vordere Schulter"]},
    {"name": "Brustdehnung liegend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Brust", "Vordere Schulter"], "secondary": []},
    {"name": "Katzenbuckel", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Rückenstrecker", "Unterer Rücken"], "secondary": ["Core"]},
    {"name": "Kindshaltung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Latissimus", "Unterer Rücken"], "secondary": ["Schultern"]},
    {"name": "Latissimus-Dehnung seitlich", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Latissimus"], "secondary": ["Seitliche Bauchmuskeln"]},
    {"name": "Schulterdehnung quer", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Hintere Schulter"], "secondary": ["Latissimus"]},
    {"name": "Überkopf-Trizepsdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trizeps"], "secondary": ["Schultern"]},
    {"name": "Schulterdehnung Türrahmen", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Vordere Schulter", "Brust"], "secondary": []},
    {"name": "Bizeps-Wanddehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Bizeps"], "secondary": ["Vordere Schulter"]},
    {"name": "Unterarm-Streckerdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Unterarm"], "secondary": []},
    {"name": "Unterarm-Beugerdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Unterarm"], "secondary": []},
    {"name": "Nackendehnung seitlich", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trapez"], "secondary": []},
    {"name": "Oberer-Trapez-Dehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trapez"], "secondary": ["Schultern"]},
    {"name": "Quad-Dehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Quadrizeps"], "secondary": ["Hüftbeuger"]},
    {"name": "Hüftbeuger-Dehnung (Ausfallschritt)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Hüftbeuger", "Quadrizeps"], "secondary": ["Gesäß"]},
    {"name": "Adduktoren-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Quadrizeps"], "secondary": []},
    {"name": "Beinrückseiten-Dehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Beinbizeps"], "secondary": ["Waden"]},
    {"name": "Beinrückseiten-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Beinbizeps"], "secondary": []},
    {"name": "Gesäßdehnung liegend (Piriformis)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Gesäß"], "secondary": ["Unterer Rücken"]},
    {"name": "Tauben-Pose", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Gesäß", "Hüftbeuger"], "secondary": ["Unterer Rücken"]},
    {"name": "Wadendehnung an der Wand", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Waden"], "secondary": []},
    {"name": "Schollenmuskel-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Waden"], "secondary": []},
    {"name": "Kobra-Dehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Bauch", "Core"], "secondary": ["Unterer Rücken"]},
    {"name": "Seitliche Rumpfdehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Seitliche Bauchmuskeln"], "secondary": ["Latissimus"]},
    {"name": "Drehsitz (Wirbelsäulen-Rotation)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Core", "Seitliche Bauchmuskeln"], "secondary": ["Unterer Rücken", "Gesäß"]},
]


def upgrade() -> None:
    conn = op.get_bind()
    for s in STRETCHES:
        # Skip if already exists
        exists = conn.execute(
            sa.text("SELECT id FROM exercise WHERE name = :name"),
            {"name": s["name"]},
        ).fetchone()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO exercise (name, category, equipment, primary_muscles_json, secondary_muscles_json, is_compound, is_selected) "
                "VALUES (:name, :category, :equipment, :primary, :secondary, 0, 1)"
            ),
            {
                "name": s["name"],
                "category": s["category"],
                "equipment": s["equipment"],
                "primary": json.dumps(s["muscles"], ensure_ascii=False),
                "secondary": json.dumps(s["secondary"], ensure_ascii=False),
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for s in STRETCHES:
        conn.execute(
            sa.text("DELETE FROM exercise WHERE name = :name AND category = 'Dehnung'"),
            {"name": s["name"]},
        )
