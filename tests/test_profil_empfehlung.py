"""Nutzerprofil, Ausruestungsfilter, Empfehlungen und Schritte ueber die API.

Der Kerntest ist ``test_empfehlung_schlaegt_nichts_vor_das_nicht_geht``: er
haelt den Befund fest, mit dem diese Runde begann. Die alte
Empfehlungslogik las den gesamten Katalog und schlug auf einem Konto mit
Kurzhanteln und Klimmzugstange Beinpresse und Kabelzug-Crossover vor.
"""

from datetime import date, timedelta

import pytest

from app.models import Exercise
from app.services.empfehlung import EmpfehlungsService
from app.services.profil import ProfilService


@pytest.fixture
def katalog(db_session):
    """Ein kleiner Katalog mit klaren Ausruestungs-Anforderungen."""
    eintraege = [
        ("Liegestütze P", "Brust", "Körpergewicht", [], {"brust_mitte": 1.0}, 0.64),
        ("Klimmzüge P", "Rücken", "Körpergewicht", ["klimmzugstange"],
         {"latissimus": 1.0}, 1.0),
        ("Beinpresse P", "Beine", "Maschine", ["beinpresse"],
         {"vastus_lateralis": 1.0}, 0.0),
        ("Kabelzug-Crossover P", "Brust", "Kabelzug", ["kabelzug"],
         {"brust_mitte": 1.0}, 0.0),
        ("Goblet-Kniebeugen P", "Beine", "Kurzhantel", ["kurzhantel"],
         {"vastus_lateralis": 1.0, "gluteus_maximus": 0.8}, 0.0),
    ]
    angelegt = []
    for name, kat, equip, benoetigt, muskeln, kg in eintraege:
        ex = Exercise(name=name, category=kat, equipment=equip,
                      is_compound=True, kg_anteil=kg, pause_s=90)
        ex.muskel_anteile = muskeln
        ex.benoetigt = benoetigt
        db_session.add(ex)
        angelegt.append(ex)
    db_session.commit()
    return angelegt


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------

def test_profil_wird_beim_ersten_zugriff_angelegt(client):
    antwort = client.get("/api/profil")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["eingerichtet"] is False
    assert daten["geraete"] == []
    assert daten["gewichtsschritt_kg"] == 2.5


def test_profil_speichern(client):
    antwort = client.put("/api/profil", json={
        "geraete": ["kurzhantel", "klimmzugstange"],
        "erfahrung": "fortgeschritten",
        "ziel": "kraft",
        "gewichtsschritt_kg": 2.0,
        "koerpergewicht_kg": 82.5,
    })
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["geraete"] == ["kurzhantel", "klimmzugstange"]
    assert daten["eingerichtet"] is True
    assert daten["zielbereich_wdh"] == [3, 6]
    assert daten["gewichtsschritt_kg"] == 2.0


def test_unbekanntes_geraet_faellt_weg_statt_zu_scheitern(client):
    """Eine ältere App-Fassung kann ein Gerät schicken, das es nicht mehr
    gibt. Dafür soll nicht das ganze Profil unspeicherbar werden."""
    antwort = client.put("/api/profil", json={
        "geraete": ["kurzhantel", "gibt-es-nicht"],
    })
    assert antwort.status_code == 200
    assert antwort.json()["geraete"] == ["kurzhantel"]


def test_vorlage_setzt_die_geraete(client):
    antwort = client.post("/api/profil/vorlage/heim_klein")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert set(daten["geraete"]) == {"kurzhantel", "klimmzugstange"}
    assert daten["eingerichtet"] is True


def test_unbekannte_vorlage_meldet_klar(client):
    antwort = client.post("/api/profil/vorlage/gibt-es-nicht")
    assert antwort.status_code == 422


def test_geraeteliste_enthaelt_keine_selbstverstaendlichkeiten(client):
    antwort = client.get("/api/profil/geraete")
    assert antwort.status_code == 200
    ids = {g["id"] for g in antwort.json()}
    assert "kurzhantel" in ids
    assert "boden" not in ids
    assert "wand" not in ids


# ---------------------------------------------------------------------------
# Ausruestungsfilter
# ---------------------------------------------------------------------------

def test_uebungsliste_ungefiltert_zeigt_alles(client, katalog):
    antwort = client.get("/api/exercises?limit=200")
    namen = {e["name"] for e in antwort.json()}
    assert "Beinpresse P" in namen


def test_nur_machbar_filtert_nach_ausruestung(client, katalog):
    client.put("/api/profil", json={"geraete": ["kurzhantel", "klimmzugstange"]})
    antwort = client.get("/api/exercises?nur_machbar=true&limit=200")
    namen = {e["name"] for e in antwort.json()}
    assert "Liegestütze P" in namen
    assert "Klimmzüge P" in namen
    assert "Goblet-Kniebeugen P" in namen
    assert "Beinpresse P" not in namen
    assert "Kabelzug-Crossover P" not in namen


def test_uebung_meldet_was_ihr_fehlt(client, katalog):
    client.put("/api/profil", json={"geraete": []})
    antwort = client.get("/api/exercises?limit=200")
    beinpresse = next(e for e in antwort.json() if e["name"] == "Beinpresse P")
    assert beinpresse["machbar"] is False
    assert "Beinpresse" in beinpresse["fehlt_namen"]


def test_luecken_nennen_den_ersatz(client, katalog):
    client.put("/api/profil", json={"geraete": ["band"]})
    antwort = client.get("/api/profil/luecken")
    assert antwort.status_code == 200
    eintraege = {e["name"]: e for e in antwort.json()}
    crossover = eintraege["Kabelzug-Crossover P"]
    assert crossover["mit_ersatz"] is True
    assert "Widerstandsbänder" in crossover["ersatz_namen"]


# ---------------------------------------------------------------------------
# Empfehlung
# ---------------------------------------------------------------------------

def test_empfehlung_schlaegt_nichts_vor_das_nicht_geht(db_session, katalog):
    """★ Der Befund, mit dem diese Runde begann."""
    ProfilService(db_session).aktualisieren(
        {"geraete": ["kurzhantel", "klimmzugstange"]})
    db_session.commit()

    svc = EmpfehlungsService(db_session)
    gruppen = svc.empfehlen(anzahl_gruppen=10)
    vorgeschlagen = {u.name for g in gruppen for u in g.uebungen}
    assert vorgeschlagen, "Es kam gar kein Vorschlag"
    assert "Beinpresse P" not in vorgeschlagen
    assert "Kabelzug-Crossover P" not in vorgeschlagen


def test_abgewaehlte_uebung_wird_nicht_empfohlen(db_session, katalog, client):
    ProfilService(db_session).aktualisieren({"geraete": ["kurzhantel"]})
    db_session.commit()
    goblet = next(e for e in katalog if e.name == "Goblet-Kniebeugen P")
    client.patch(f"/api/exercises/{goblet.id}/select", json={"is_selected": False})

    svc = EmpfehlungsService(db_session)
    gruppen = svc.empfehlen(anzahl_gruppen=10)
    vorgeschlagen = {u.name for g in gruppen for u in g.uebungen}
    assert "Goblet-Kniebeugen P" not in vorgeschlagen


def test_progressionsreihe_liefert_nur_eine_stufe(db_session):
    """★★ Gemessen kamen "Liegestütze" und "Liegestütze an der Wand"
    nebeneinander heraus, also Stufe 3 und Stufe 1 derselben Sache."""
    for stufe, name in ((1, "Wand-LS"), (3, "Normale LS"), (6, "Einarmige LS")):
        ex = Exercise(name=name, category="Brust", equipment="Körpergewicht",
                      is_compound=True, kg_anteil=0.6,
                      reihe="ls-test", stufe=stufe)
        ex.muskel_anteile = {"brust_mitte": 1.0}
        db_session.add(ex)
    db_session.commit()

    ProfilService(db_session).aktualisieren({"erfahrung": "fortgeschritten"})
    db_session.commit()

    svc = EmpfehlungsService(db_session)
    gefiltert = {u.name for u in svc._stufenfilter(svc.verfuegbare_uebungen())}
    aus_der_reihe = gefiltert & {"Wand-LS", "Normale LS", "Einarmige LS"}
    assert len(aus_der_reihe) == 1, f"Mehrere Stufen zugleich: {aus_der_reihe}"
    # Fortgeschritten startet auf Stufe 3.
    assert aus_der_reihe == {"Normale LS"}


def test_stufe_folgt_dem_was_tatsaechlich_gemacht_wurde(db_session):
    """Wer schon die einarmige Variante trainiert, bekommt nicht die Wand."""
    angelegt = {}
    for stufe, name in ((1, "Wand-LS2"), (3, "Normale LS2"), (6, "Einarmige LS2")):
        ex = Exercise(name=name, category="Brust", equipment="Körpergewicht",
                      is_compound=True, kg_anteil=0.6,
                      reihe="ls-test2", stufe=stufe)
        ex.muskel_anteile = {"brust_mitte": 1.0}
        db_session.add(ex)
        angelegt[name] = ex
    db_session.commit()

    from datetime import datetime, timezone
    from app.models import Workout, WorkoutSet
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    db_session.add(WorkoutSet(workout_id=w.id, exercise_id=angelegt["Einarmige LS2"].id,
                              set_number=1, reps=5, is_completed=True,
                              is_warmup=False, set_type="normal"))
    db_session.commit()

    svc = EmpfehlungsService(db_session)
    assert svc.aktuelle_stufen()["ls-test2"] == 6
    gefiltert = {u.name for u in svc._stufenfilter(svc.verfuegbare_uebungen())}
    assert "Einarmige LS2" in gefiltert
    assert "Wand-LS2" not in gefiltert


def test_uebungsliste_zeigt_weiter_alle_stufen(client, db_session):
    """★ Der Stufenfilter greift nur bei Vorschlägen. In der Übungsliste und
    im Plan-Editor will man alle Varianten sehen."""
    for stufe, name in ((1, "Wand-LS3"), (3, "Normale LS3")):
        ex = Exercise(name=name, category="Brust", equipment="Körpergewicht",
                      kg_anteil=0.6, reihe="ls-test3", stufe=stufe)
        ex.muskel_anteile = {"brust_mitte": 1.0}
        db_session.add(ex)
    db_session.commit()
    namen = {e["name"] for e in client.get("/api/exercises?limit=200").json()}
    assert {"Wand-LS3", "Normale LS3"} <= namen


def test_dehnung_ist_nicht_im_trainingsvorschlag(db_session):
    ex = Exercise(name="Wadendehnung P", category="Dehnung",
                  equipment="Körpergewicht", ist_zeit=True)
    ex.muskel_anteile = {"gastrocnemius": 1.0}
    db_session.add(ex)
    db_session.commit()

    svc = EmpfehlungsService(db_session)
    verfuegbar = {u.name for u in svc.verfuegbare_uebungen()}
    assert "Wadendehnung P" not in verfuegbar
    mit = {u.name for u in svc.verfuegbare_uebungen(mit_dehnung=True)}
    assert "Wadendehnung P" in mit


def test_einheitsvorschlag_haelt_die_zeit_ein(db_session, katalog):
    ProfilService(db_session).aktualisieren(
        {"geraete": ["kurzhantel", "klimmzugstange"]})
    db_session.commit()
    svc = EmpfehlungsService(db_session)
    einheit = svc.einheit_vorschlagen(dauer_minuten=20)
    assert einheit["geplante_minuten"] <= 20
    assert einheit["uebungen"]


def test_empfehlung_ueber_die_api(client, katalog):
    client.put("/api/profil", json={"geraete": ["kurzhantel", "klimmzugstange"]})
    antwort = client.get("/api/analyse/empfehlung")
    assert antwort.status_code == 200
    gruppen = antwort.json()
    assert gruppen
    assert all(g["begruendung"] for g in gruppen)


def test_registry_ueber_die_api(client):
    antwort = client.get("/api/analyse/registry")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert len(daten["regionen"]) == 10
    assert len(daten["gruppen"]) == 19
    assert len(daten["muskeln"]) >= 40
    # Jeder Muskel zeigt auf eine gelieferte Gruppe: sonst kann das
    # Koerpermodell ihn nicht einordnen.
    gruppen_ids = {g["id"] for g in daten["gruppen"]}
    for muskel in daten["muskeln"]:
        assert muskel["gruppe"] in gruppen_ids


# ---------------------------------------------------------------------------
# Feinauswahl im Koerpermodell
# ---------------------------------------------------------------------------

def test_muskelauswahl_liefert_verschiedene_listen(db_session, client):
    """★★ Der Befund aus der Oberflaeche: wer im Oberschenkel eine bestimmte
    Partie antippte, bekam immer dieselbe Liste, weil alles auf die Region
    ``quads`` abgebildet wurde."""
    strecker = Exercise(name="Beinstrecker T", category="Beine", equipment="Maschine")
    strecker.muskel_anteile = {"rectus_femoris": 1.0, "vastus_lateralis": 1.0,
                               "vastus_medialis": 1.0}
    adduktion = Exercise(name="Sumo-Kniebeuge T", category="Beine",
                         equipment="Körpergewicht", kg_anteil=0.7)
    adduktion.muskel_anteile = {"adduktoren": 1.0, "gluteus_maximus": 0.9}
    db_session.add_all([strecker, adduktion])
    db_session.commit()

    quad = client.get("/api/exercises?muscle=vastus_medialis&limit=50").json()
    add = client.get("/api/exercises?muscle=adduktoren&limit=50").json()
    assert {e["name"] for e in quad} != {e["name"] for e in add}
    assert "Beinstrecker T" in {e["name"] for e in quad}
    assert "Beinstrecker T" not in {e["name"] for e in add}
    assert "Sumo-Kniebeuge T" in {e["name"] for e in add}


def test_muskelauswahl_nimmt_auch_den_alten_freitextnamen(db_session, client):
    ex = Exercise(name="Kniebeuge T2", category="Beine", equipment="Langhantel")
    ex.muskel_anteile = {"vastus_lateralis": 1.0}
    db_session.add(ex)
    db_session.commit()
    antwort = client.get("/api/exercises?muscle=Quadrizeps&limit=50")
    assert antwort.status_code == 200
    assert "Kniebeuge T2" in {e["name"] for e in antwort.json()}


def test_gruppenauswahl_sortiert_nach_anteil(db_session, client):
    haupt = Exercise(name="Bizeps-Curl T", category="Arme", equipment="Kurzhantel")
    haupt.muskel_anteile = {"bizeps_lang": 1.0}
    neben = Exercise(name="Klimmzug T", category="Rücken", equipment="Körpergewicht",
                     kg_anteil=1.0)
    neben.muskel_anteile = {"latissimus": 1.0, "bizeps_lang": 0.6}
    db_session.add_all([haupt, neben])
    db_session.commit()
    antwort = client.get("/api/exercises?gruppe=bizeps&limit=50").json()
    namen = [e["name"] for e in antwort]
    assert namen.index("Bizeps-Curl T") < namen.index("Klimmzug T")


# ---------------------------------------------------------------------------
# Schritte
# ---------------------------------------------------------------------------

def test_schritte_melden_und_lesen(client):
    heute = date.today()
    antwort = client.put("/api/schritte", json=[
        {"datum": heute.isoformat(), "schritte": 8200, "quelle": "health_connect"},
        {"datum": (heute - timedelta(days=1)).isoformat(), "schritte": 4300,
         "quelle": "health_connect"},
    ])
    assert antwort.status_code == 200
    uebersicht = client.get("/api/schritte?tage=7").json()
    assert uebersicht["heute"] == 8200
    assert uebersicht["erfasste_tage"] == 2
    assert uebersicht["aktive_tage"] == 1
    assert uebersicht["schnitt"] == 6250


def test_derselbe_tag_wird_ueberschrieben_nicht_verdoppelt(client):
    """★ Ein Handy schiebt denselben Tag mehrfach, während die Schritte
    weiterlaufen. Mit POST entstünden Duplikate."""
    heute = date.today().isoformat()
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 3000, "quelle": "health_connect"}])
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 9000, "quelle": "health_connect"}])
    uebersicht = client.get("/api/schritte").json()
    assert uebersicht["erfasste_tage"] == 1
    assert uebersicht["heute"] == 9000


def test_kleinerer_wert_derselben_quelle_senkt_nicht(client):
    """Eine unvollständige Abfrage ist kein Rückgang."""
    heute = date.today().isoformat()
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 9000, "quelle": "health_connect"}])
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 100, "quelle": "health_connect"}])
    assert client.get("/api/schritte").json()["heute"] == 9000


def test_andere_quelle_darf_korrigieren(client):
    heute = date.today().isoformat()
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 9000, "quelle": "health_connect"}])
    client.put("/api/schritte", json=[
        {"datum": heute, "schritte": 100, "quelle": "manuell"}])
    assert client.get("/api/schritte").json()["heute"] == 100


def test_letzter_tag_ohne_daten(client):
    assert client.get("/api/schritte/letzter-tag").json()["datum"] is None
