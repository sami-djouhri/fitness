"""Seed standard exercises and an example Push/Pull/Legs plan."""

import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, engine, Base
from app.models import Exercise, Plan, PlanDay, PlanExercise

EXERCISES = [
    # Brust
    {"name": "Bankdrücken", "category": "Brust", "equipment": "Langhantel", "muscles": ["Brust"], "secondary": ["Trizeps", "Vordere Schulter"], "compound": True},
    {"name": "Schrägbankdrücken", "category": "Brust", "equipment": "Langhantel", "muscles": ["Obere Brust"], "secondary": ["Trizeps", "Vordere Schulter"], "compound": True},
    {"name": "Kurzhantel-Bankdrücken", "category": "Brust", "equipment": "Kurzhantel", "muscles": ["Brust"], "secondary": ["Trizeps", "Vordere Schulter"], "compound": True},
    {"name": "Kurzhantel-Fliegende", "category": "Brust", "equipment": "Kurzhantel", "muscles": ["Brust"], "secondary": ["Vordere Schulter"], "compound": False},
    {"name": "Kabelzug-Crossover", "category": "Brust", "equipment": "Kabelzug", "muscles": ["Brust"], "secondary": ["Vordere Schulter"], "compound": False},
    {"name": "Liegestütze", "category": "Brust", "equipment": "Körpergewicht", "muscles": ["Brust"], "secondary": ["Trizeps", "Vordere Schulter", "Core"], "compound": True},
    {"name": "Dips", "category": "Brust", "equipment": "Körpergewicht", "muscles": ["Brust", "Trizeps"], "secondary": ["Vordere Schulter"], "compound": True},
    # Rücken
    {"name": "Kreuzheben", "category": "Rücken", "equipment": "Langhantel", "muscles": ["Unterer Rücken", "Beinbizeps", "Gesäß"], "secondary": ["Trapez", "Quadrizeps", "Unterarm", "Core"], "compound": True},
    {"name": "Langhantelrudern", "category": "Rücken", "equipment": "Langhantel", "muscles": ["Latissimus", "Trapez"], "secondary": ["Bizeps", "Hintere Schulter", "Unterarm"], "compound": True},
    {"name": "Kurzhantelrudern", "category": "Rücken", "equipment": "Kurzhantel", "muscles": ["Latissimus", "Trapez"], "secondary": ["Bizeps", "Hintere Schulter"], "compound": True},
    {"name": "Latzug", "category": "Rücken", "equipment": "Kabelzug", "muscles": ["Latissimus"], "secondary": ["Bizeps", "Hintere Schulter", "Unterarm"], "compound": True},
    {"name": "Klimmzüge", "category": "Rücken", "equipment": "Körpergewicht", "muscles": ["Latissimus"], "secondary": ["Bizeps", "Unterarm", "Hintere Schulter"], "compound": True},
    {"name": "Kabelrudern sitzend", "category": "Rücken", "equipment": "Kabelzug", "muscles": ["Latissimus", "Trapez"], "secondary": ["Bizeps", "Hintere Schulter"], "compound": True},
    {"name": "Face Pulls", "category": "Rücken", "equipment": "Kabelzug", "muscles": ["Hintere Schulter", "Trapez"], "secondary": ["Seitliche Schulter"], "compound": False},
    # Schultern
    {"name": "Schulterdrücken", "category": "Schultern", "equipment": "Langhantel", "muscles": ["Vordere Schulter", "Seitliche Schulter"], "secondary": ["Trizeps", "Trapez"], "compound": True},
    {"name": "Kurzhantel-Schulterdrücken", "category": "Schultern", "equipment": "Kurzhantel", "muscles": ["Vordere Schulter", "Seitliche Schulter"], "secondary": ["Trizeps", "Trapez"], "compound": True},
    {"name": "Seitheben", "category": "Schultern", "equipment": "Kurzhantel", "muscles": ["Seitliche Schulter"], "secondary": ["Trapez"], "compound": False},
    {"name": "Frontheben", "category": "Schultern", "equipment": "Kurzhantel", "muscles": ["Vordere Schulter"], "secondary": ["Seitliche Schulter"], "compound": False},
    {"name": "Reverse Flys", "category": "Schultern", "equipment": "Kurzhantel", "muscles": ["Hintere Schulter"], "secondary": ["Trapez"], "compound": False},
    {"name": "Aufrechtes Rudern", "category": "Schultern", "equipment": "Langhantel", "muscles": ["Seitliche Schulter", "Trapez"], "secondary": ["Bizeps", "Vordere Schulter"], "compound": True},
    # Arme
    {"name": "Bizeps-Curls Langhantel", "category": "Arme", "equipment": "Langhantel", "muscles": ["Bizeps"], "secondary": ["Unterarm"], "compound": False},
    {"name": "Bizeps-Curls Kurzhantel", "category": "Arme", "equipment": "Kurzhantel", "muscles": ["Bizeps"], "secondary": ["Unterarm"], "compound": False},
    {"name": "Hammer-Curls", "category": "Arme", "equipment": "Kurzhantel", "muscles": ["Bizeps", "Unterarm"], "secondary": [], "compound": False},
    {"name": "Trizepsdrücken am Kabel", "category": "Arme", "equipment": "Kabelzug", "muscles": ["Trizeps"], "secondary": [], "compound": False},
    {"name": "Französisches Drücken", "category": "Arme", "equipment": "Langhantel", "muscles": ["Trizeps"], "secondary": ["Schultern"], "compound": False},
    {"name": "Trizeps-Kickbacks", "category": "Arme", "equipment": "Kurzhantel", "muscles": ["Trizeps"], "secondary": [], "compound": False},
    # Beine
    {"name": "Kniebeugen", "category": "Beine", "equipment": "Langhantel", "muscles": ["Quadrizeps", "Gesäß"], "secondary": ["Core", "Unterer Rücken", "Beinbizeps"], "compound": True},
    {"name": "Frontkniebeugen", "category": "Beine", "equipment": "Langhantel", "muscles": ["Quadrizeps"], "secondary": ["Core", "Gesäß"], "compound": True},
    {"name": "Beinpresse", "category": "Beine", "equipment": "Maschine", "muscles": ["Quadrizeps", "Gesäß"], "secondary": ["Beinbizeps"], "compound": True},
    {"name": "Rumänisches Kreuzheben", "category": "Beine", "equipment": "Langhantel", "muscles": ["Beinbizeps", "Gesäß"], "secondary": ["Unterer Rücken", "Core"], "compound": True},
    {"name": "Beinstrecker", "category": "Beine", "equipment": "Maschine", "muscles": ["Quadrizeps"], "secondary": [], "compound": False},
    {"name": "Beinbeuger", "category": "Beine", "equipment": "Maschine", "muscles": ["Beinbizeps"], "secondary": ["Waden"], "compound": False},
    {"name": "Ausfallschritte", "category": "Beine", "equipment": "Kurzhantel", "muscles": ["Quadrizeps", "Gesäß"], "secondary": ["Beinbizeps", "Core"], "compound": True},
    {"name": "Wadenheben stehend", "category": "Beine", "equipment": "Maschine", "muscles": ["Waden"], "secondary": [], "compound": False},
    {"name": "Hip Thrusts", "category": "Beine", "equipment": "Langhantel", "muscles": ["Gesäß"], "secondary": ["Beinbizeps", "Core"], "compound": True},
    # Core
    {"name": "Plank", "category": "Core", "equipment": "Körpergewicht", "muscles": ["Core"], "secondary": ["Schultern", "Gesäß"], "compound": False},
    {"name": "Crunches", "category": "Core", "equipment": "Körpergewicht", "muscles": ["Bauch"], "secondary": [], "compound": False},
    {"name": "Beinheben hängend", "category": "Core", "equipment": "Körpergewicht", "muscles": ["Untere Bauchmuskeln", "Hüftbeuger"], "secondary": ["Core"], "compound": False},
    {"name": "Russian Twists", "category": "Core", "equipment": "Körpergewicht", "muscles": ["Seitliche Bauchmuskeln"], "secondary": ["Core"], "compound": False},
    {"name": "Cable Woodchops", "category": "Core", "equipment": "Kabelzug", "muscles": ["Seitliche Bauchmuskeln", "Core"], "secondary": ["Schultern"], "compound": False},
    # Cardio
    {"name": "Laufband", "category": "Cardio", "equipment": "Maschine", "muscles": ["Beine", "Herz-Kreislauf"], "secondary": [], "compound": False},
    {"name": "Rudergerät", "category": "Cardio", "equipment": "Maschine", "muscles": ["Ganzkörper", "Herz-Kreislauf"], "secondary": [], "compound": True},
    # Dehnung: Brust
    {"name": "Brustdehnung an der Wand", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Brust"], "secondary": ["Vordere Schulter"], "compound": False},
    {"name": "Brustdehnung liegend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Brust", "Vordere Schulter"], "secondary": [], "compound": False},
    # Dehnung: Rücken
    {"name": "Katzenbuckel", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Rückenstrecker", "Unterer Rücken"], "secondary": ["Core"], "compound": False},
    {"name": "Kindshaltung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Latissimus", "Unterer Rücken"], "secondary": ["Schultern"], "compound": False},
    {"name": "Latissimus-Dehnung seitlich", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Latissimus"], "secondary": ["Seitliche Bauchmuskeln"], "compound": False},
    # Dehnung: Schultern
    {"name": "Schulterdehnung quer", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Hintere Schulter"], "secondary": ["Latissimus"], "compound": False},
    {"name": "Überkopf-Trizepsdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trizeps"], "secondary": ["Schultern"], "compound": False},
    {"name": "Schulterdehnung Türrahmen", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Vordere Schulter", "Brust"], "secondary": [], "compound": False},
    # Dehnung: Arme
    {"name": "Bizeps-Wanddehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Bizeps"], "secondary": ["Vordere Schulter"], "compound": False},
    {"name": "Unterarm-Streckerdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Unterarm"], "secondary": [], "compound": False},
    {"name": "Unterarm-Beugerdehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Unterarm"], "secondary": [], "compound": False},
    # Dehnung: Trapez
    {"name": "Nackendehnung seitlich", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trapez"], "secondary": [], "compound": False},
    {"name": "Oberer-Trapez-Dehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Trapez"], "secondary": ["Schultern"], "compound": False},
    # Dehnung: Beine (Quads)
    {"name": "Quad-Dehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Quadrizeps"], "secondary": ["Hüftbeuger"], "compound": False},
    {"name": "Hüftbeuger-Dehnung (Ausfallschritt)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Hüftbeuger", "Quadrizeps"], "secondary": ["Gesäß"], "compound": False},
    {"name": "Adduktoren-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Quadrizeps"], "secondary": [], "compound": False},
    # Dehnung: Beine (Hamstrings)
    {"name": "Beinrückseiten-Dehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Beinbizeps"], "secondary": ["Waden"], "compound": False},
    {"name": "Beinrückseiten-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Beinbizeps"], "secondary": [], "compound": False},
    {"name": "Gesäßdehnung liegend (Piriformis)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Gesäß"], "secondary": ["Unterer Rücken"], "compound": False},
    {"name": "Tauben-Pose", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Gesäß", "Hüftbeuger"], "secondary": ["Unterer Rücken"], "compound": False},
    # Dehnung: Waden
    {"name": "Wadendehnung an der Wand", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Waden"], "secondary": [], "compound": False},
    {"name": "Schollenmuskel-Dehnung sitzend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Waden"], "secondary": [], "compound": False},
    # Dehnung: Core
    {"name": "Kobra-Dehnung", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Bauch", "Core"], "secondary": ["Unterer Rücken"], "compound": False},
    {"name": "Seitliche Rumpfdehnung stehend", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Seitliche Bauchmuskeln"], "secondary": ["Latissimus"], "compound": False},
    {"name": "Drehsitz (Wirbelsäulen-Rotation)", "category": "Dehnung", "equipment": "Körpergewicht", "muscles": ["Core", "Seitliche Bauchmuskeln"], "secondary": ["Unterer Rücken", "Gesäß"], "compound": False},
]

# Push/Pull/Legs plan template (exercise name -> plan config)
PPL_PLAN = {
    "name": "Push/Pull/Legs",
    "description": "Klassischer 6-Tage PPL-Split für Fortgeschrittene",
    "days": [
        {
            "name": "Push A",
            "day_of_week": 0,
            "exercises": [
                {"name": "Bankdrücken", "sets": 4, "reps_min": 5, "reps_max": 5, "rpe": 8.0, "rest": 180},
                {"name": "Kurzhantel-Schulterdrücken", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 120},
                {"name": "Schrägbankdrücken", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 120},
                {"name": "Seitheben", "sets": 4, "reps_min": 12, "reps_max": 15, "rest": 60},
                {"name": "Trizepsdrücken am Kabel", "sets": 3, "reps_min": 10, "reps_max": 15, "rest": 60},
            ],
        },
        {
            "name": "Pull A",
            "day_of_week": 1,
            "exercises": [
                {"name": "Kreuzheben", "sets": 3, "reps_min": 5, "reps_max": 5, "rpe": 8.0, "rest": 180},
                {"name": "Klimmzüge", "sets": 4, "reps_min": 6, "reps_max": 10, "rest": 120},
                {"name": "Kabelrudern sitzend", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 90},
                {"name": "Face Pulls", "sets": 4, "reps_min": 15, "reps_max": 20, "rest": 60},
                {"name": "Bizeps-Curls Langhantel", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 60},
            ],
        },
        {
            "name": "Legs A",
            "day_of_week": 2,
            "exercises": [
                {"name": "Kniebeugen", "sets": 4, "reps_min": 5, "reps_max": 5, "rpe": 8.0, "rest": 180},
                {"name": "Rumänisches Kreuzheben", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 120},
                {"name": "Beinpresse", "sets": 3, "reps_min": 10, "reps_max": 15, "rest": 90},
                {"name": "Beinbeuger", "sets": 3, "reps_min": 10, "reps_max": 15, "rest": 60},
                {"name": "Wadenheben stehend", "sets": 4, "reps_min": 12, "reps_max": 15, "rest": 60},
            ],
        },
        {
            "name": "Push B",
            "day_of_week": 3,
            "exercises": [
                {"name": "Schulterdrücken", "sets": 4, "reps_min": 5, "reps_max": 5, "rpe": 8.0, "rest": 180},
                {"name": "Kurzhantel-Bankdrücken", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 120},
                {"name": "Kabelzug-Crossover", "sets": 3, "reps_min": 12, "reps_max": 15, "rest": 60},
                {"name": "Seitheben", "sets": 4, "reps_min": 12, "reps_max": 15, "rest": 60},
                {"name": "Französisches Drücken", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 90},
            ],
        },
        {
            "name": "Pull B",
            "day_of_week": 4,
            "exercises": [
                {"name": "Langhantelrudern", "sets": 4, "reps_min": 5, "reps_max": 5, "rpe": 8.0, "rest": 180},
                {"name": "Latzug", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 90},
                {"name": "Kurzhantelrudern", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 90},
                {"name": "Reverse Flys", "sets": 3, "reps_min": 12, "reps_max": 15, "rest": 60},
                {"name": "Hammer-Curls", "sets": 3, "reps_min": 10, "reps_max": 12, "rest": 60},
            ],
        },
        {
            "name": "Legs B",
            "day_of_week": 5,
            "exercises": [
                {"name": "Frontkniebeugen", "sets": 4, "reps_min": 6, "reps_max": 8, "rpe": 8.0, "rest": 180},
                {"name": "Hip Thrusts", "sets": 3, "reps_min": 8, "reps_max": 12, "rest": 120},
                {"name": "Ausfallschritte", "sets": 3, "reps_min": 10, "reps_max": 12, "rest": 90},
                {"name": "Beinstrecker", "sets": 3, "reps_min": 12, "reps_max": 15, "rest": 60},
                {"name": "Wadenheben stehend", "sets": 4, "reps_min": 12, "reps_max": 15, "rest": 60},
            ],
        },
    ],
}


def seed():
    db = SessionLocal()
    try:
        # Skip if exercises already exist
        if db.query(Exercise).first():
            print("Daten bereits vorhanden – überspringe Seed.")
            return

        # Create exercises
        name_to_id: dict[str, int] = {}
        for ex_data in EXERCISES:
            ex = Exercise(
                name=ex_data["name"],
                category=ex_data["category"],
                equipment=ex_data["equipment"],
                is_compound=ex_data["compound"],
            )
            ex.primary_muscles = ex_data["muscles"]
            ex.secondary_muscles = ex_data.get("secondary", [])
            db.add(ex)
            db.flush()
            name_to_id[ex.name] = ex.id

        # Create PPL plan
        plan = Plan(
            name=PPL_PLAN["name"],
            description=PPL_PLAN["description"],
            is_active=True,
        )
        db.add(plan)
        db.flush()

        for sort_idx, day_data in enumerate(PPL_PLAN["days"]):
            day = PlanDay(
                plan_id=plan.id,
                name=day_data["name"],
                day_of_week=day_data.get("day_of_week"),
                sort_order=sort_idx,
            )
            db.add(day)
            db.flush()

            for ex_idx, ex_data in enumerate(day_data["exercises"]):
                pe = PlanExercise(
                    plan_day_id=day.id,
                    exercise_id=name_to_id[ex_data["name"]],
                    sort_order=ex_idx,
                    target_sets=ex_data["sets"],
                    target_reps_min=ex_data["reps_min"],
                    target_reps_max=ex_data["reps_max"],
                    target_rpe=ex_data.get("rpe"),
                    rest_seconds=ex_data["rest"],
                )
                db.add(pe)

        db.commit()
        print(f"Seed abgeschlossen: {len(EXERCISES)} Übungen, 1 Plan mit {len(PPL_PLAN['days'])} Tagen.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
