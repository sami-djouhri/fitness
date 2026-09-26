"""Zeitpunkte gehen mit Zonenangabe nach draussen.

★ Der Fund, der nur im Bild sichtbar war: der Trainings-Timer stand bei einer
gerade angelegten Session auf 2:04:32. Beide Seiten rechneten fuer sich
richtig. SQLite speichert die Zeitpunkte ohne Zone, Pydantic gab sie genauso
weiter ("2026-09-12T13:06:04"), und die Werte sind UTC. Ein Browser liest eine
ISO-Zeit ohne Offset aber als ORTSZEIT, im Sommer also zwei Stunden vor der
Wahrheit.

Deshalb hier festgenagelt: ohne diese Pruefung faellt das Format beim
naechsten Umbau still zurueck, und der Fehler ist im Code unsichtbar.
"""

from datetime import datetime, timezone


def _hat_zone(wert: str) -> bool:
    """Traegt der Zeitstempel eine Zonenangabe (Z oder +hh:mm)?"""
    return wert.endswith("Z") or "+" in wert[10:] or "-" in wert[10:]


def test_workout_zeitpunkte_mit_zone(client):
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    assert _hat_zone(w["started_at"]), f"ohne Zone: {w['started_at']}"

    fertig = client.post(f"/api/workouts/{w['id']}/finish").json()
    assert _hat_zone(fertig["finished_at"])


def test_startzeit_ist_wirklich_jetzt(client):
    """Die Probe auf den Fehler: der Abstand zu jetzt muss klein sein.

    Wird die Zone wieder weggelassen und der Wert als Ortszeit gelesen, liegt
    er je nach Zone Stunden daneben. Diese Pruefung rechnet wie der Browser.
    """
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    gelesen = datetime.fromisoformat(w["started_at"])
    abstand = abs((datetime.now(timezone.utc) - gelesen).total_seconds())
    assert abstand < 60, f"Startzeit liegt {abstand:.0f} s neben jetzt"


def test_satz_abhakzeit_mit_zone(client):
    ex = client.post("/api/exercises", json={
        "name": "Bankdrücken", "category": "Brust", "equipment": "Langhantel",
    }).json()["id"]
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    satz = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": ex, "set_number": 1, "weight_kg": 80, "reps": 8,
    }).json()
    assert _hat_zone(satz["completed_at"])


def test_rekord_und_zusammenfassung_mit_zone(client):
    ex = client.post("/api/exercises", json={
        "name": "Kniebeugen", "category": "Beine", "equipment": "Langhantel",
    }).json()["id"]
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": ex, "set_number": 1, "weight_kg": 100, "reps": 5,
    })

    prs = client.get("/api/progress/prs").json()
    assert prs and _hat_zone(prs[0]["achieved_at"])

    zusammenfassung = client.get("/api/progress/summary").json()
    assert _hat_zone(zusammenfassung["last_workout"])


def test_plan_erstellzeit_mit_zone(client):
    plan = client.post("/api/plans", json={"name": "PPL"}).json()
    assert _hat_zone(plan["created_at"])
