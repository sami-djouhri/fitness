"""Benachrichtigungskanal: Regeln, Gedaechtnis, Mandanten, Nutzlast.

★ Der Regressionstest am Ende ist der Grund fuer den Umbau. Die Logik lag bis
2026-09-12 in einem Bash-Skript, das die Nutzlast mit Zeichenkettenersetzung
in Python-Quelltext baute:

    payload="$(python3 -c "print(json.dumps({'uebung': '''$name'''}))")"

Ein Uebungsname mit drei Anfuehrungszeichen darin schloss die Zeichenkette und
fuehrte den Rest als Code aus. Nachgestellt am 2026-09-12: ein Name mit
``''' + __import__('os').popen('id -un').read() + '''`` lieferte ``host``
in der Nutzlast. Uebungsnamen kann jeder angemeldete Nutzer setzen, in der
oeffentlichen Demo also auch ein Besucher, und das Skript lief als host auf
dem kanonischen Host.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models import PersonalRecord, Workout
from app.services import anstoss

BOESER_NAME = "Bankdruecken''' + __import__('os').popen('id -un').read() + '''"


@pytest.fixture(autouse=True)
def _kanal_aus(monkeypatch):
    """Nichts wirklich senden. Der Publisher wird je Test ersetzt."""
    monkeypatch.setattr(settings, "MQTT_HOST", "")
    yield


class _Sammler:
    """Attrappe des Publishers: merkt sich, was gesendet wuerde."""

    def __init__(self, erfolg=True):
        self.gesendet: list[tuple[str, str, dict]] = []
        self._erfolg = erfolg

    def publish(self, entity, action, nutzlast):
        self.gesendet.append((entity, action, nutzlast))
        return self._erfolg

    def zustand(self):
        return {"konfiguriert": True, "gesendet": len(self.gesendet)}


@pytest.fixture
def sammler(monkeypatch):
    s = _Sammler()
    import app.mqtt
    monkeypatch.setattr(app.mqtt, "publisher", s)
    return s


def _uebung(client, name="Bankdrücken"):
    return client.post("/api/exercises", json={
        "name": name, "category": "Brust", "equipment": "Langhantel",
    }).json()["id"]


# --- Regeln ---

def test_ohne_training_wird_erinnert(client, db_session):
    meldungen = anstoss.faellige_meldungen(db_session)
    schluessel = [m.schluessel for m in meldungen]
    assert "erinnerung" in schluessel
    erinnerung = next(m for m in meldungen if m.schluessel == "erinnerung")
    assert erinnerung.nutzlast["text"] == "Noch kein Training erfasst"
    assert erinnerung.nutzlast["tage_ohne_training"] is None


def test_frisches_training_erinnert_nicht(client, db_session):
    client.post("/api/workouts", json={"name": "Heute"})
    assert [m.schluessel for m in anstoss.faellige_meldungen(db_session)] == []


def test_alte_pause_erinnert_mit_trainingstag(client, db_session):
    plan = client.post("/api/plans", json={"name": "PPL", "is_active": True}).json()
    client.post(f"/api/plans/{plan['id']}/activate")
    client.post(f"/api/plans/{plan['id']}/days", json={"name": "Push"})

    w = client.post("/api/workouts", json={"name": "Lange her"}).json()
    alt = datetime.now(timezone.utc) - timedelta(days=5)
    db_session.get(Workout, w["id"]).started_at = alt
    db_session.commit()

    meldungen = anstoss.faellige_meldungen(db_session)
    erinnerung = next(m for m in meldungen if m.schluessel == "erinnerung")
    assert erinnerung.nutzlast["tage_ohne_training"] == 5
    assert "Dran ist: Push" in erinnerung.nutzlast["text"]


def test_rekord_wird_gemeldet(client, db_session):
    eid = _uebung(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 100, "reps": 5,
    })

    schluessel = [m.schluessel for m in anstoss.faellige_meldungen(db_session)]
    assert any(s.startswith("rekord:") for s in schluessel)


# --- Gedaechtnis ---

def test_zweimal_laufen_meldet_einmal(client, db_session, sammler):
    zuerst = anstoss.melden(db_session, "mandant-a")
    db_session.commit()
    assert len(zuerst) >= 1
    assert all(m["gesendet"] for m in zuerst)

    danach = anstoss.melden(db_session, "mandant-a")
    db_session.commit()
    assert danach == [], "dieselbe Sache darf nicht zweimal gehen"


def test_erinnerung_wiederholt_sich_nach_dem_abstand(client, db_session, sammler):
    from app.models import AnstossMerker

    anstoss.melden(db_session, "mandant-a")
    db_session.commit()

    merker = db_session.query(AnstossMerker).filter(
        AnstossMerker.schluessel == "erinnerung"
    ).first()
    merker.gemeldet_am = datetime.now(timezone.utc) - timedelta(hours=21)
    db_session.commit()

    erneut = anstoss.melden(db_session, "mandant-a")
    assert [m["schluessel"] for m in erneut] == ["erinnerung"]


def test_fehlgeschlagene_meldung_wird_nicht_vermerkt(client, db_session, monkeypatch):
    """Sonst waere der erste echte Anlass genau der, der verloren geht."""
    import app.mqtt
    monkeypatch.setattr(app.mqtt, "publisher", _Sammler(erfolg=False))

    zuerst = anstoss.melden(db_session, "mandant-a")
    db_session.commit()
    assert zuerst and not any(m["gesendet"] for m in zuerst)

    # Jetzt traegt der Kanal wieder.
    monkeypatch.setattr(app.mqtt, "publisher", _Sammler(erfolg=True))
    erneut = anstoss.melden(db_session, "mandant-a")
    assert [m["schluessel"] for m in erneut] == [m["schluessel"] for m in zuerst]


def test_trockenlauf_vermerkt_nichts(client, db_session, sammler):
    vorschau = anstoss.melden(db_session, "mandant-a", trockenlauf=True)
    db_session.commit()
    assert vorschau and not any(m["gesendet"] for m in vorschau)
    assert sammler.gesendet == [], "im Trockenlauf wird nicht gesendet"

    echt = anstoss.melden(db_session, "mandant-a")
    assert [m["schluessel"] for m in echt] == [m["schluessel"] for m in vorschau]


# --- Nutzlast ---

def test_nutzlast_traegt_den_mandanten(client, db_session, sammler):
    anstoss.melden(db_session, "mandant-a")
    assert all(n["owner_sub"] == "mandant-a" for _e, _a, n in sammler.gesendet)
    assert all(n["quelle"] == "fitness" for _e, _a, n in sammler.gesendet)


def test_uebungsname_mit_anfuehrungszeichen_ist_harmlos(client, db_session, sammler):
    """Regressionstest gegen die Code-Injection des alten Bash-Skripts."""
    eid = _uebung(client, BOESER_NAME)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 100, "reps": 5,
    })

    anstoss.melden(db_session, "mandant-a")
    rekorde = [n for _e, a, n in sammler.gesendet if a == "erreicht"]
    assert rekorde, "der Rekord muss gemeldet werden"
    # Der Name kommt unveraendert durch, als Daten. Kein Kommando ausgefuehrt.
    assert rekorde[0]["uebung"] == BOESER_NAME
    assert "host" not in rekorde[0]["uebung"]

    # Und er laesst sich als JSON serialisieren, ohne etwas zu zerlegen.
    import json
    assert json.loads(json.dumps(rekorde[0]))["uebung"] == BOESER_NAME


def test_rekord_mit_hoeherem_wert_ist_eine_neue_meldung(client, db_session, sammler):
    eid = _uebung(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 100, "reps": 5,
    })
    anstoss.melden(db_session, "mandant-a")
    db_session.commit()

    pr = db_session.query(PersonalRecord).filter(
        PersonalRecord.pr_type == "max_weight"
    ).first()
    pr.value = 105.0
    pr.achieved_at = datetime.now(timezone.utc)
    db_session.commit()

    erneut = anstoss.melden(db_session, "mandant-a")
    assert any("105" in m["schluessel"] for m in erneut)


# --- Endpunkt ---

def test_endpunkt_ohne_token_gesperrt(client, monkeypatch):
    monkeypatch.setattr(settings, "ANSTOSS_TOKEN", "")
    assert client.post("/api/anstoss/pruefen").status_code == 503


def test_endpunkt_mit_falschem_token(client, monkeypatch):
    monkeypatch.setattr(settings, "ANSTOSS_TOKEN", "richtig")
    r = client.post("/api/anstoss/pruefen", headers={"X-Anstoss-Token": "falsch"})
    assert r.status_code == 401


def test_endpunkt_trockenlauf(client, db_session, monkeypatch, sammler):
    monkeypatch.setattr(settings, "ANSTOSS_TOKEN", "richtig")
    client.post("/api/workouts", json={"name": "Damit ein Mandant existiert"})
    db_session.commit()

    r = client.post(
        "/api/anstoss/pruefen?trockenlauf=true",
        headers={"X-Anstoss-Token": "richtig"},
    )
    assert r.status_code == 200
    assert "mandanten" in r.json()
    assert sammler.gesendet == []
