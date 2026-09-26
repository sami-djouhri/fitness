"""Aus dem Training folgt der Kalorienbedarf.

★ Die Luecke in der App-Kette: MealPrep rechnet ``TDEE = BMR x
Aktivitaetsfaktor``, und der Faktor kam aus einem Auswahlfeld, das von Hand
gesetzt wird und auf "moderate" vorbelegt ist. Wer vier Mal pro Woche schwer
trainiert, bekam dieselben Kalorien vorgeschlagen wie jemand, der die App nur
eingerichtet hat. Der Adapter dafuer lag fertig da und hatte keinen Aufrufer.

Damit war die Kette Training, Bedarf, Gerichte, Einkaufsliste an ihrer ersten
Stelle offen. Alles dahinter existierte schon: mealprep fragt lager nach dem
Vorrat und fuellt die Einkaufsliste.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Workout
from app.services import aktivitaet


def _uebung(client, name="Bankdrücken"):
    return client.post("/api/exercises", json={
        "name": name, "category": "Brust", "equipment": "Langhantel",
    }).json()["id"]


def _training(client, db_session, eid, tage_her: float, abgehakt=True):
    """Ein Training mit einem Satz, vor N Tagen."""
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 80, "reps": 8,
        "is_completed": abgehakt,
    })
    db_session.get(Workout, w["id"]).started_at = (
        datetime.now(timezone.utc) - timedelta(days=tage_her)
    )
    db_session.commit()
    return w["id"]


# --- Ableitung ---

def test_ohne_training_wird_nichts_behauptet(client, db_session):
    """★ Keine Daten heisst nicht kein Training.

    Ohne diese Schwelle haette die Uebertragung den Tagesbedarf des Nutzers
    von 2259 auf rund 1750 kcal gesenkt, weil er seine Trainings (noch) nicht
    erfasst, nicht weil er keine macht.
    """
    n = aktivitaet.ableiten(db_session)
    assert n.belastbar is False
    assert aktivitaet.uebertragen_faellig(db_session, n) is False
    assert "Erst 0 von 4 Trainings erfasst" in n.begruendung


def test_vier_pro_woche_ist_maessig_aktiv(client, db_session):
    eid = _uebung(client)
    # 16 Trainings in 28 Tagen = 4 pro Woche
    for i in range(16):
        _training(client, db_session, eid, tage_her=i * 1.7)

    n = aktivitaet.ableiten(db_session)
    assert n.trainings_pro_woche == 4.0
    assert n.stufe == "moderate"
    assert n.faktor == 1.55
    assert "4.0 Trainings pro Woche" in n.begruendung


def test_taeglich_ist_sehr_aktiv(client, db_session):
    eid = _uebung(client)
    for i in range(28):
        _training(client, db_session, eid, tage_her=i)

    n = aktivitaet.ableiten(db_session)
    assert n.trainings_pro_woche == 7.0
    assert n.stufe == "very_active"


def test_einmal_pro_woche_ist_leicht(client, db_session):
    eid = _uebung(client)
    for i in range(4):
        _training(client, db_session, eid, tage_her=i * 7)

    n = aktivitaet.ableiten(db_session)
    assert n.trainings_pro_woche == 1.0
    assert n.stufe == "light"
    assert n.belastbar is True, "vier Trainings sind die Schwelle"


def test_drei_trainings_sind_noch_nicht_belastbar(client, db_session):
    eid = _uebung(client)
    for i in range(3):
        _training(client, db_session, eid, tage_her=i * 7)

    n = aktivitaet.ableiten(db_session)
    assert n.belastbar is False
    assert aktivitaet.uebertragen_faellig(db_session, n) is False


def test_geplantes_training_erhoeht_den_bedarf_nicht(client, db_session):
    """Sonst isst man mehr, weil man vorhatte zu trainieren."""
    eid = _uebung(client)
    for i in range(16):
        _training(client, db_session, eid, tage_her=i * 1.7, abgehakt=False)

    n = aktivitaet.ableiten(db_session)
    assert n.trainings_im_fenster == 0
    assert n.stufe == "sedentary"


def test_leeres_training_zaehlt_nicht(client, db_session):
    """Eine Session ohne einen einzigen Satz ist kein Training."""
    for _ in range(16):
        client.post("/api/workouts", json={"name": "Nur gestartet"})
    db_session.commit()

    assert aktivitaet.ableiten(db_session).trainings_im_fenster == 0


def test_alte_trainings_fallen_aus_dem_fenster(client, db_session):
    eid = _uebung(client)
    for i in range(16):
        _training(client, db_session, eid, tage_her=40 + i)

    assert aktivitaet.ableiten(db_session).trainings_im_fenster == 0


# --- Uebertragung ---

def test_uebertragung_nur_bei_aenderung(client, db_session):
    """Es ist ein Schreibzugriff in ein fremdes Profil."""
    eid = _uebung(client)
    for i in range(4):
        _training(client, db_session, eid, tage_her=i * 7)
    n = aktivitaet.ableiten(db_session)
    assert aktivitaet.uebertragen_faellig(db_session, n) is True

    aktivitaet.uebertragung_vermerken(db_session, n)
    db_session.commit()
    assert aktivitaet.uebertragen_faellig(db_session, n) is False


def test_neue_stufe_wird_wieder_faellig(client, db_session):
    eid = _uebung(client)
    for i in range(4):
        _training(client, db_session, eid, tage_her=i * 7)
    zuerst = aktivitaet.ableiten(db_session)
    aktivitaet.uebertragung_vermerken(db_session, zuerst)
    db_session.commit()

    for i in range(16):
        _training(client, db_session, eid, tage_her=i * 1.7)

    danach = aktivitaet.ableiten(db_session)
    assert danach.stufe != zuerst.stufe
    assert aktivitaet.uebertragen_faellig(db_session, danach) is True


def test_beenden_uebertraegt_die_stufe(client, db_session, monkeypatch):
    """Der Aufrufer, der vorher fehlte."""
    uebertragen: list[str] = []

    async def merke(level, owner_sub=None):
        uebertragen.append(level)
        return True

    from app.services import mealprep_adapter
    monkeypatch.setattr(mealprep_adapter, "update_activity_level", merke)

    eid = _uebung(client)
    for i in range(4):
        _training(client, db_session, eid, tage_her=i * 7)

    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 80, "reps": 8,
    })
    r = client.post(f"/api/workouts/{w['id']}/finish")
    assert r.status_code == 200
    assert uebertragen == ["light"], "Stufe muss nach MealPrep gehen"


def test_beenden_ohne_genug_daten_uebertraegt_nichts(client, monkeypatch):
    uebertragen: list[str] = []

    async def merke(level, owner_sub=None):
        uebertragen.append(level)
        return True

    from app.services import mealprep_adapter
    monkeypatch.setattr(mealprep_adapter, "update_activity_level", merke)

    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/finish")
    assert uebertragen == [], "ein einziges Training ist keine Messung"


def test_zweites_beenden_uebertraegt_nicht_erneut(client, db_session, monkeypatch):
    uebertragen: list[str] = []

    async def merke(level, owner_sub=None):
        uebertragen.append(level)
        return True

    from app.services import mealprep_adapter
    monkeypatch.setattr(mealprep_adapter, "update_activity_level", merke)

    eid = _uebung(client)
    for i in range(6):
        _training(client, db_session, eid, tage_her=i * 4)

    for _ in range(2):
        w = client.post("/api/workouts", json={"name": "Test"}).json()
        client.post(f"/api/workouts/{w['id']}/sets", json={
            "exercise_id": eid, "set_number": 1, "weight_kg": 80, "reps": 8,
        })
        client.post(f"/api/workouts/{w['id']}/finish")

    assert len(uebertragen) == 1, "dieselbe Stufe nicht zweimal schreiben"


def test_ausfall_von_mealprep_blockiert_das_beenden_nicht(client, monkeypatch):
    async def stirbt(level, owner_sub=None):
        raise RuntimeError("MealPrep schlaeft")

    from app.services import mealprep_adapter
    monkeypatch.setattr(mealprep_adapter, "update_activity_level", stirbt)

    w = client.post("/api/workouts", json={"name": "Test"}).json()
    assert client.post(f"/api/workouts/{w['id']}/finish").status_code == 200


# --- Endpunkt ---

def test_endpunkt_zeigt_die_kette(client, db_session):
    eid = _uebung(client)
    for i in range(16):
        _training(client, db_session, eid, tage_her=i * 1.7)

    daten = client.get("/api/progress/aktivitaetsniveau").json()
    assert daten["belastbar"] is True
    assert daten["stufe"] == "moderate"
    assert daten["faktor"] == 1.55
    assert daten["trainings_pro_woche"] == 4.0
    assert daten["fenster_tage"] == 28
    assert daten["an_mealprep_uebertragen"] is False
