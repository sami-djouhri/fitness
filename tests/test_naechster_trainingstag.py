"""Welcher Trainingstag ansteht.

``next_plan_day`` stand seit Bestehen in beiden Schemas, im Backend wie im
Frontend-Typ, und wurde nie gefuellt. Damit fehlte die Antwort auf die einzige
Frage, die man beim Oeffnen der App hat.

Zwei Wege, in dieser Reihenfolge: ein fester Wochentag ist die ausdrueckliche
Angabe des Nutzers und schlaegt die Ableitung; sonst Rotation nach dem letzten
trainierten Tag.
"""

from datetime import datetime, timezone


def _plan_mit_tagen(client, tage: list[str], wochentage: list[int | None] | None = None):
    plan = client.post("/api/plans", json={"name": "PPL", "is_active": True}).json()
    if not plan["is_active"]:
        client.post(f"/api/plans/{plan['id']}/activate")
    ids = []
    for i, name in enumerate(tage):
        rumpf = {"name": name, "sort_order": i}
        if wochentage and wochentage[i] is not None:
            rumpf["day_of_week"] = wochentage[i]
        ids.append(client.post(f"/api/plans/{plan['id']}/days", json=rumpf).json()["id"])
    return plan, ids


def test_ohne_plan_kein_vorschlag(client):
    daten = client.get("/api/progress/summary").json()
    assert daten["next_plan_day"] is None
    assert daten["next_plan_day_id"] is None


def test_erster_tag_wenn_noch_nie_trainiert(client):
    _plan, ids = _plan_mit_tagen(client, ["Push", "Pull", "Legs"])
    daten = client.get("/api/progress/summary").json()
    assert daten["next_plan_day"] == "Push"
    assert daten["next_plan_day_id"] == ids[0]


def test_rotation_nach_dem_letzten_training(client):
    _plan, ids = _plan_mit_tagen(client, ["Push", "Pull", "Legs"])

    client.post("/api/workouts", json={"plan_day_id": ids[0]})
    assert client.get("/api/progress/summary").json()["next_plan_day"] == "Pull"

    client.post("/api/workouts", json={"plan_day_id": ids[1]})
    assert client.get("/api/progress/summary").json()["next_plan_day"] == "Legs"


def test_rotation_laeuft_um(client):
    _plan, ids = _plan_mit_tagen(client, ["Push", "Pull"])
    client.post("/api/workouts", json={"plan_day_id": ids[1]})
    assert client.get("/api/progress/summary").json()["next_plan_day"] == "Push"


def test_fester_wochentag_schlaegt_die_rotation(client):
    heute = datetime.now(timezone.utc).weekday()
    _plan, ids = _plan_mit_tagen(
        client, ["Push", "Pull", "Heute"], wochentage=[None, None, heute],
    )
    # Die Rotation wuerde "Push" sagen, der feste Wochentag gewinnt.
    daten = client.get("/api/progress/summary").json()
    assert daten["next_plan_day"] == "Heute"
    assert daten["next_plan_day_id"] == ids[2]


def test_freies_training_stoert_die_rotation_nicht(client):
    _plan, ids = _plan_mit_tagen(client, ["Push", "Pull"])
    client.post("/api/workouts", json={"plan_day_id": ids[0]})
    client.post("/api/workouts", json={"name": "Freies Training"})
    assert client.get("/api/progress/summary").json()["next_plan_day"] == "Pull", \
        "ein Training ohne Plan-Tag darf die Reihenfolge nicht verschieben"


def test_nur_der_aktive_plan_zaehlt(client):
    _plan_mit_tagen(client, ["Push", "Pull"])
    zweiter = client.post("/api/plans", json={"name": "Ganzkoerper"}).json()
    client.post(f"/api/plans/{zweiter['id']}/days", json={"name": "Ganzkoerper A"})
    client.post(f"/api/plans/{zweiter['id']}/activate")

    assert client.get("/api/progress/summary").json()["next_plan_day"] == "Ganzkoerper A"
