"""Der Trainingsplan muss im Training ankommen.

Bis 2026-09 uebernahm ``POST /api/workouts`` mit ``plan_day_id`` nur den Namen
des Tages. Die gepflegten Uebungen samt Ziel-Wiederholungen und Pausenzeiten
blieben liegen, ``get_plan_day_exercises`` hatte keinen Aufrufer. Praktisch
startete man "Push" und stand vor einem leeren Bildschirm.

Zweiter Teil: ein vorbefuellter Satz ist geplant, nicht gemacht. Ohne diese
Unterscheidung zaehlt die Statistik fuenf geplante Uebungen als absolviert,
sobald man nach zwei aufhoert.
"""


def _uebung(client, name="Bankdrücken", kategorie="Brust"):
    r = client.post("/api/exercises", json={
        "name": name, "category": kategorie, "equipment": "Langhantel",
    })
    return r.json()["id"]


def _trainingstag(client, uebungen, target_sets=3, rest_seconds=120):
    """Plan mit einem Tag und den uebergebenen Uebungen."""
    plan = client.post("/api/plans", json={"name": "PPL"}).json()
    tag = client.post(f"/api/plans/{plan['id']}/days", json={"name": "Push"}).json()
    for i, eid in enumerate(uebungen):
        client.post(f"/api/plans/days/{tag['id']}/exercises", json={
            "exercise_id": eid,
            "sort_order": i,
            "target_sets": target_sets,
            "target_reps_min": 6,
            "target_reps_max": 10,
            "rest_seconds": rest_seconds,
        })
    return tag["id"]


def test_plan_tag_fuellt_die_session(client):
    a = _uebung(client, "Bankdrücken")
    b = _uebung(client, "Schulterdrücken", "Schultern")
    tag = _trainingstag(client, [a, b], target_sets=3)

    w = client.post("/api/workouts", json={"plan_day_id": tag}).json()

    assert w["name"] == "Push", "Name des Tages uebernommen"
    assert len(w["sets"]) == 6, "zwei Uebungen mit je drei Saetzen"
    assert [s["exercise_id"] for s in w["sets"]].count(a) == 3
    assert [s["set_number"] for s in w["sets"] if s["exercise_id"] == a] == [1, 2, 3]


def test_vorbefuellte_saetze_sind_nicht_abgehakt(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a])
    w = client.post("/api/workouts", json={"plan_day_id": tag}).json()

    assert all(s["is_completed"] is False for s in w["sets"])
    assert all(s["completed_at"] is None for s in w["sets"])


def test_plan_vorgaben_kommen_mit(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a], rest_seconds=150)
    w = client.post("/api/workouts", json={"plan_day_id": tag}).json()

    vorgaben = {v["exercise_id"]: v for v in w["plan_targets"]}
    assert vorgaben[a]["rest_seconds"] == 150, "gepflegte Pause statt fester 90 s"
    assert vorgaben[a]["target_reps_min"] == 6
    assert vorgaben[a]["target_reps_max"] == 10
    assert vorgaben[a]["exercise_name"] == "Bankdrücken"

    # Erneutes Laden liefert sie ebenfalls: die Checkliste ueberlebt ein
    # Neuladen der Seite im Gym.
    erneut = client.get(f"/api/workouts/{w['id']}").json()
    assert len(erneut["plan_targets"]) == 1


def test_freies_training_hat_keine_vorgaben(client):
    w = client.post("/api/workouts", json={"name": "Freies Training"}).json()
    assert w["sets"] == []
    assert w["plan_targets"] == []


def test_prefill_abschaltbar(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a])
    w = client.post("/api/workouts", json={"plan_day_id": tag, "prefill": False}).json()
    assert w["sets"] == []
    assert len(w["plan_targets"]) == 1, "Vorgaben bleiben sichtbar"


def test_empfohlene_uebungen_landen_in_der_session(client):
    """Das Dashboard zeigte drei Uebungen und startete ein leeres Training."""
    a = _uebung(client, "Kniebeugen", "Beine")
    b = _uebung(client, "Kreuzheben", "Ruecken")

    w = client.post("/api/workouts", json={
        "name": "Beine Training", "exercise_ids": [a, b],
    }).json()

    assert len(w["sets"]) == 6
    assert {s["exercise_id"] for s in w["sets"]} == {a, b}
    assert all(s["is_completed"] is False for s in w["sets"])


def test_doppelte_uebung_wird_einmal_vorbefuellt(client):
    a = _uebung(client)
    w = client.post("/api/workouts", json={"exercise_ids": [a, a]}).json()
    assert len(w["sets"]) == 3


def test_unbekannte_uebung_wird_abgelehnt(client):
    # 422 ist hier die hausinterne Antwort auf DomainError (app/main.py).
    r = client.post("/api/workouts", json={"exercise_ids": [4242]})
    assert r.status_code == 422
    assert "Übung" in r.json()["error"]


def test_geplante_saetze_zaehlen_nicht_ins_volumen(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a])

    # Erst ein echter Satz, damit das Vorbefuellen ein letztes Gewicht findet.
    erst = client.post("/api/workouts", json={"name": "Erst"}).json()
    client.post(f"/api/workouts/{erst['id']}/sets", json={
        "exercise_id": a, "set_number": 1, "weight_kg": 100, "reps": 5,
    })
    volumen_vorher = client.get("/api/progress/summary").json()["total_volume_7d"]
    assert volumen_vorher == 500

    # Die vorbefuellte Session tragt dasselbe Gewicht, aber nur als Vorgabe.
    w = client.post("/api/workouts", json={"plan_day_id": tag}).json()
    assert all(s["weight_kg"] == 100 for s in w["sets"]), "letztes Gewicht vorgeschlagen"

    assert client.get("/api/progress/summary").json()["total_volume_7d"] == volumen_vorher, \
        "Vorgaben duerfen das Volumen nicht erhoehen"


def test_geplanter_satz_erzeugt_keinen_rekord(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a])
    client.post("/api/workouts", json={"plan_day_id": tag})

    assert client.get("/api/progress/prs").json() == []


def test_abhaken_laesst_den_satz_zaehlen(client):
    a = _uebung(client)
    tag = _trainingstag(client, [a], target_sets=1)
    w = client.post("/api/workouts", json={"plan_day_id": tag}).json()
    satz = w["sets"][0]

    r = client.put(f"/api/workouts/sets/{satz['id']}", json={
        "weight_kg": 90, "reps": 8, "is_completed": True,
    })
    assert r.status_code == 200
    assert r.json()["is_completed"] is True
    assert r.json()["completed_at"] is not None

    assert client.get("/api/progress/summary").json()["total_volume_7d"] == 720
    prs = client.get("/api/progress/prs").json()
    assert prs, "abgehakter Satz stellt Rekorde auf"


def test_haken_wieder_entfernen(client):
    a = _uebung(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    satz = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": a, "set_number": 1, "weight_kg": 60, "reps": 10,
    }).json()
    assert satz["is_completed"] is True, "von Hand eingetragen heisst gemacht"

    r = client.put(f"/api/workouts/sets/{satz['id']}", json={"is_completed": False}).json()
    assert r["is_completed"] is False
    assert r["completed_at"] is None
    assert client.get("/api/progress/summary").json()["total_volume_7d"] == 0


def test_geplanter_satz_ist_keine_historie(client):
    """Der Ueberlastungsvorschlag darf nicht aus Vorgaben rechnen."""
    a = _uebung(client)
    tag = _trainingstag(client, [a])
    client.post("/api/workouts", json={"plan_day_id": tag})

    vorschlag = client.get(f"/api/workouts/suggestions?exercise_id={a}").json()
    assert vorschlag["reason"] == "Noch keine Daten vorhanden"

    verlauf = client.get(f"/api/progress/exercise/{a}/history").json()
    assert verlauf == []


def test_heatmap_zeigt_session_ohne_abgehakten_satz(client):
    """Aussenverbund: die Session darf nicht aus dem Kalender fallen."""
    a = _uebung(client)
    tag = _trainingstag(client, [a])
    client.post("/api/workouts", json={"plan_day_id": tag})

    tage = client.get("/api/progress/calendar").json()
    assert len(tage) == 1, "Trainingstag bleibt sichtbar"
    assert tage[0]["workouts"] == 1
    assert tage[0]["sets"] == 0, "aber ohne gezaehlte Saetze"
