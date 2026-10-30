"""Der geteilte Uebungskatalog trug Zustand, der einer Person gehoert.

``exercise`` steht bewusst nicht unter dem Mandanten-Scoping (app/tenant.py):
die Eintraege aus dem Seed sollen allen zur Verfuegung stehen. Daraus folgte
bis 2026-09 aber dreierlei, das niemand wollte:

- ``is_selected`` ("habe ich in meinem Studio") sass am geteilten Katalog. Wer
  abwaehlte, waehlte allen ab.
- ``POST``/``PUT``/``DELETE /api/exercises`` waren ohne Eigentuemer offen. In
  der oeffentlichen Demo konnte ein Besucher den Katalog aendern.
- ``delete`` prueffte keine Verwendung: eine Uebung aus einem fremden Plan war
  loeschbar.

Die Mandanten-Tests laufen gegen einen eigenen sessionmaker mit angehaengten
Scoping-Ereignissen. Die ``client``-Fixture in conftest.py benutzt eine
Session OHNE diese Ereignisse, ein Mandantentest darueber waere gruen, ohne
etwas zu pruefen.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.tenant as tenant
from app.db import Base
from app.models import Exercise
from app.schemas import ExerciseCreate
from app.services.exercises import ExerciseService

MANDANT_A = "mandant-a"
MANDANT_B = "mandant-b"


@pytest.fixture
def sitzungen():
    motor = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(motor)
    Sitzung = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    event.listen(Sitzung, "do_orm_execute", tenant._apply_tenant_scope)
    event.listen(Sitzung, "before_flush", tenant._stamp_tenant)
    yield Sitzung


def dienst(Sitzung, sub: str) -> tuple[ExerciseService, object]:
    s = Sitzung()
    s.info["owner_sub"] = sub
    return ExerciseService(s), s


def katalogeintrag(Sitzung, name="Bankdrücken") -> int:
    """Eintrag ohne Urheber, wie aus dem Seed."""
    s = Sitzung()
    s.info["owner_sub"] = "seed"
    ex = Exercise(name=name, category="Brust", equipment="Langhantel")
    s.add(ex)
    s.commit()
    eid = ex.id
    s.close()
    return eid


# --- Auswahl je Mandant ---

def test_abwaehlen_gilt_nur_fuer_den_eigenen_mandanten(sitzungen):
    eid = katalogeintrag(sitzungen)

    a, sa = dienst(sitzungen, MANDANT_A)
    a.auswahl_setzen(eid, False)
    sa.commit()
    assert a.auswahl([eid]) == {eid: False}
    sa.close()

    b, sb = dienst(sitzungen, MANDANT_B)
    assert b.auswahl([eid]) == {}, "B hat nichts abgewaehlt und darf es nicht sehen"
    sb.close()


def test_ohne_eintrag_gilt_ausgewaehlt(sitzungen):
    eid = katalogeintrag(sitzungen)
    a, sa = dienst(sitzungen, MANDANT_A)
    assert a.auswahl([eid]) == {}, "kein Eintrag heisst ausgewaehlt"
    sa.close()


def test_wiederanwaehlen_ueberschreibt_statt_zu_doppeln(sitzungen):
    eid = katalogeintrag(sitzungen)
    a, sa = dienst(sitzungen, MANDANT_A)
    a.auswahl_setzen(eid, False)
    sa.commit()
    a.auswahl_setzen(eid, True)
    sa.commit()
    assert a.auswahl([eid]) == {eid: True}
    sa.close()


# --- Sichtbarkeit selbst angelegter Uebungen ---

def test_eigene_uebung_bleibt_beim_urheber(sitzungen):
    a, sa = dienst(sitzungen, MANDANT_A)
    eigene = a.create(ExerciseCreate(
        name="Beinpresse Gerät 3", category="Beine", equipment="Maschine",
    ))
    sa.commit()
    eid = eigene.id
    assert eigene.created_by_sub == MANDANT_A
    assert [e.id for e in a.list_all()] == [eid]
    sa.close()

    b, sb = dienst(sitzungen, MANDANT_B)
    assert b.list_all() == [], "fremd angelegte Uebung ist nicht sichtbar"
    with pytest.raises(Exception):
        b.get(eid)
    sb.close()


def test_seed_eintrag_sehen_alle(sitzungen):
    eid = katalogeintrag(sitzungen, "Kniebeugen")
    for sub in (MANDANT_A, MANDANT_B):
        d, s = dienst(sitzungen, sub)
        assert [e.id for e in d.list_all()] == [eid]
        s.close()


def test_fremde_uebung_nicht_aenderbar(sitzungen):
    a, sa = dienst(sitzungen, MANDANT_A)
    eigene = a.create(ExerciseCreate(name="Meine Übung", category="Beine", equipment="Maschine"))
    sa.commit()
    eid = eigene.id
    sa.close()

    from app.schemas import ExerciseUpdate
    b, sb = dienst(sitzungen, MANDANT_B)
    with pytest.raises(Exception):
        b.update(eid, ExerciseUpdate(name="Umbenannt"))
    with pytest.raises(Exception):
        b.delete(eid)
    sb.close()

    # Und der Urheber darf weiterhin.
    a2, sa2 = dienst(sitzungen, MANDANT_A)
    a2.update(eid, ExerciseUpdate(name="Umbenannt"))
    sa2.commit()
    assert a2.get(eid).name == "Umbenannt"
    sa2.close()


# --- Schutz des gemeinsamen Katalogs, ueber die API ---

def _uebung_per_api(client, name="Bankdrücken"):
    return client.post("/api/exercises", json={
        "name": name, "category": "Brust", "equipment": "Langhantel",
    }).json()["id"]


def test_api_kennzeichnet_eigene_eintraege(client):
    eid = _uebung_per_api(client)
    daten = client.get(f"/api/exercises/{eid}").json()
    assert daten["is_eigene"] is True
    assert daten["is_selected"] is True


def test_seed_eintrag_ist_nicht_aenderbar(client, db_session):
    """Ein Eintrag ohne Urheber gehoert dem gemeinsamen Katalog."""
    ex = Exercise(name="Klimmzüge", category="Rücken", equipment="Körpergewicht")
    db_session.add(ex)
    db_session.commit()

    r = client.put(f"/api/exercises/{ex.id}", json={"name": "Umbenannt"})
    assert r.status_code == 422
    assert "gemeinsamen Katalog" in r.json()["error"]

    r = client.delete(f"/api/exercises/{ex.id}")
    assert r.status_code == 422
    assert client.get(f"/api/exercises/{ex.id}").json()["name"] == "Klimmzüge"


def test_verwendete_uebung_wird_nicht_geloescht(client):
    eid = _uebung_per_api(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 80, "reps": 8,
    })

    r = client.delete(f"/api/exercises/{eid}")
    assert r.status_code == 422
    assert "wird verwendet" in r.json()["error"]
    assert r.json()["details"]["in_workouts"] is True
    # Der Satz haengt noch dran, die Historie ist unversehrt.
    assert len(client.get(f"/api/workouts/{w['id']}").json()["sets"]) == 1


def test_uebung_im_plan_wird_nicht_geloescht(client):
    eid = _uebung_per_api(client)
    plan = client.post("/api/plans", json={"name": "PPL"}).json()
    tag = client.post(f"/api/plans/{plan['id']}/days", json={"name": "Push"}).json()
    client.post(f"/api/plans/days/{tag['id']}/exercises", json={"exercise_id": eid})

    r = client.delete(f"/api/exercises/{eid}")
    assert r.status_code == 422
    assert r.json()["details"]["in_plaenen"] is True


def test_unbenutzte_eigene_uebung_ist_loeschbar(client):
    eid = _uebung_per_api(client, "Nur zum Testen")
    assert client.delete(f"/api/exercises/{eid}").status_code == 204
    assert client.get(f"/api/exercises/{eid}").status_code == 422


def test_abwaehlen_ueber_die_api(client):
    eid = _uebung_per_api(client)
    r = client.patch(f"/api/exercises/{eid}/select", json={"is_selected": False})
    assert r.status_code == 200
    assert r.json()["is_selected"] is False
    assert client.get(f"/api/exercises/{eid}").json()["is_selected"] is False

    r = client.patch(f"/api/exercises/{eid}/select", json={"is_selected": True})
    assert r.json()["is_selected"] is True


def test_liste_traegt_den_auswahlzustand(client):
    behalten = _uebung_per_api(client, "Behalten")
    weg = _uebung_per_api(client, "Abgewählt")
    client.patch(f"/api/exercises/{weg}/select", json={"is_selected": False})

    zustand = {e["id"]: e["is_selected"] for e in client.get("/api/exercises").json()}
    assert zustand[behalten] is True
    assert zustand[weg] is False
