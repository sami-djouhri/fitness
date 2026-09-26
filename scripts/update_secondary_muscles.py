"""Update secondary_muscles_json for all existing exercises in the database."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models import Exercise

# Name → secondary muscles mapping (from seed_demo_data.py)
SECONDARY: dict[str, list[str]] = {
    "Bankdrücken": ["Trizeps", "Vordere Schulter"],
    "Schrägbankdrücken": ["Trizeps", "Vordere Schulter"],
    "Kurzhantel-Bankdrücken": ["Trizeps", "Vordere Schulter"],
    "Kurzhantel-Fliegende": ["Vordere Schulter"],
    "Kabelzug-Crossover": ["Vordere Schulter"],
    "Liegestütze": ["Trizeps", "Vordere Schulter", "Core"],
    "Dips": ["Vordere Schulter"],
    "Kreuzheben": ["Trapez", "Quadrizeps", "Unterarm", "Core"],
    "Langhantelrudern": ["Bizeps", "Hintere Schulter", "Unterarm"],
    "Kurzhantelrudern": ["Bizeps", "Hintere Schulter"],
    "Latzug": ["Bizeps", "Hintere Schulter", "Unterarm"],
    "Klimmzüge": ["Bizeps", "Unterarm", "Hintere Schulter"],
    "Kabelrudern sitzend": ["Bizeps", "Hintere Schulter"],
    "Face Pulls": ["Seitliche Schulter"],
    "Schulterdrücken": ["Trizeps", "Trapez"],
    "Kurzhantel-Schulterdrücken": ["Trizeps", "Trapez"],
    "Seitheben": ["Trapez"],
    "Frontheben": ["Seitliche Schulter"],
    "Reverse Flys": ["Trapez"],
    "Aufrechtes Rudern": ["Bizeps", "Vordere Schulter"],
    "Bizeps-Curls Langhantel": ["Unterarm"],
    "Bizeps-Curls Kurzhantel": ["Unterarm"],
    "Hammer-Curls": [],
    "Trizepsdrücken am Kabel": [],
    "Französisches Drücken": ["Schultern"],
    "Trizeps-Kickbacks": [],
    "Kniebeugen": ["Core", "Unterer Rücken", "Beinbizeps"],
    "Frontkniebeugen": ["Core", "Gesäß"],
    "Beinpresse": ["Beinbizeps"],
    "Rumänisches Kreuzheben": ["Unterer Rücken", "Core"],
    "Beinstrecker": [],
    "Beinbeuger": ["Waden"],
    "Ausfallschritte": ["Beinbizeps", "Core"],
    "Wadenheben stehend": [],
    "Hip Thrusts": ["Beinbizeps", "Core"],
    "Plank": ["Schultern", "Gesäß"],
    "Crunches": [],
    "Beinheben hängend": ["Core"],
    "Russian Twists": ["Core"],
    "Cable Woodchops": ["Schultern"],
    "Laufband": [],
    "Rudergerät": [],
}


def update():
    db = SessionLocal()
    try:
        updated = 0
        for ex in db.query(Exercise).all():
            sec = SECONDARY.get(ex.name)
            if sec is not None:
                current = ex.secondary_muscles or []
                if current != sec:
                    ex.secondary_muscles = sec
                    updated += 1
        db.commit()
        print(f"Sekundärmuskeln aktualisiert: {updated} Übungen.")
    finally:
        db.close()


if __name__ == "__main__":
    update()
