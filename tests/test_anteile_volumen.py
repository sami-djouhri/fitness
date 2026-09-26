"""Anteile, effektive Last, Wochenvolumen und Frische.

Der wichtigste Test hier ist ``test_koerpergewichtsuebung_erzeugt_volumen``:
er haelt den Befund fest, der die ganze Rechenschicht ausgeloest hat. Ohne
``kg_anteil`` ist das Volumen jedes Klimmzugs null, und wer zu Hause
trainiert, sieht in der Statistik eine Nulllinie.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Exercise, Workout, WorkoutSet
from app.services.anteile import (
    anteile, effektive_last, gruppenanteile, regionenanteile, satzvolumen,
)
from app.services.volumen import VolumenService


@pytest.fixture
def klimmzug(db_session):
    ex = Exercise(name="Klimmzüge Test", category="Rücken",
                  equipment="Körpergewicht", is_compound=True,
                  kg_anteil=1.0, muster="ziehen_vertikal")
    ex.muskel_anteile = {"latissimus": 1.0, "bizeps_lang": 0.6,
                         "unterarm_beuger": 0.5}
    ex.benoetigt = ["klimmzugstange"]
    db_session.add(ex)
    db_session.commit()
    return ex


@pytest.fixture
def curl_alt(db_session):
    """Eine Uebung im alten Format, ohne gepflegte Anteile."""
    ex = Exercise(name="Alt-Curls", category="Arme", equipment="Kurzhantel")
    ex.primary_muscles = ["Bizeps"]
    ex.secondary_muscles = ["Unterarm"]
    db_session.add(ex)
    db_session.commit()
    return ex


# ---------------------------------------------------------------------------
# Anteile
# ---------------------------------------------------------------------------

def test_gepflegte_anteile_gewinnen(klimmzug):
    werte = anteile(klimmzug)
    assert werte["latissimus"] == 1.0
    assert werte["bizeps_lang"] == 0.6


def test_altes_format_wird_abgebildet(curl_alt):
    """Selbst angelegte Uebungen tragen Freitext und muessen weiter zaehlen."""
    werte = anteile(curl_alt)
    assert werte, "Freitext-Muskeln wurden nicht aufgelöst"
    # "Bizeps" ist ein Sammelbegriff und trifft alle drei Beuger, voll.
    assert werte["bizeps_lang"] == 1.0
    assert werte["brachialis"] == 1.0
    # "Unterarm" stand in der Zweitliste und zaehlt halb.
    assert werte["unterarm_beuger"] == 0.5


def test_gruppe_zaehlt_den_hoechsten_muskel_nicht_die_summe(db_session):
    """★ Eine Kniebeuge trifft vier Quadrizeps-Köpfe mit je 1.0.

    Wuerde die Gruppe die Summe bilden, ergaebe ein Satz vier Sätze
    Quadrizeps, und jede Volumenrechnung laege um den Faktor der Köpfe daneben.
    """
    ex = Exercise(name="Kniebeuge Test", category="Beine", equipment="Langhantel")
    ex.muskel_anteile = {
        "rectus_femoris": 1.0, "vastus_lateralis": 1.0,
        "vastus_medialis": 1.0, "vastus_intermedius": 0.9,
        "gluteus_maximus": 0.8,
    }
    db_session.add(ex)
    db_session.commit()
    gruppen = gruppenanteile(ex)
    assert gruppen["quadrizeps"] == 1.0
    assert gruppen["gesaess"] == 0.8


def test_regionenanteile(klimmzug):
    regionen = regionenanteile(klimmzug)
    assert regionen["back"] == 1.0
    assert regionen["biceps"] == 0.6


# ---------------------------------------------------------------------------
# Effektive Last
# ---------------------------------------------------------------------------

def test_koerpergewichtsuebung_erzeugt_volumen(klimmzug):
    """★★ Der Befund: ohne kg_anteil ist das Volumen null."""
    assert effektive_last(klimmzug, None, 80.0) == 80.0
    assert satzvolumen(klimmzug, None, 10, 80.0) == 800.0


def test_zusatzgewicht_kommt_obendrauf(klimmzug):
    assert effektive_last(klimmzug, 10.0, 80.0) == 90.0
    assert satzvolumen(klimmzug, 10.0, 5, 80.0) == 450.0


def test_ohne_koerpergewicht_bleibt_nur_das_zusatzgewicht(klimmzug):
    """Kein geratener Wert: eine erfundene Zahl wandert sonst durch jede
    Statistik und sieht dort aus wie eine Messung."""
    assert effektive_last(klimmzug, None, None) == 0.0
    assert effektive_last(klimmzug, 15.0, None) == 15.0


def test_hantelübung_ignoriert_das_koerpergewicht(curl_alt):
    assert effektive_last(curl_alt, 20.0, 80.0) == 20.0


def test_zeitbasierte_uebung_hat_kein_volumen(db_session):
    ex = Exercise(name="Plank Test", category="Rumpf", equipment="Körpergewicht",
                  kg_anteil=0.55, ist_zeit=True)
    ex.muskel_anteile = {"transversus": 1.0}
    db_session.add(ex)
    db_session.commit()
    assert satzvolumen(ex, None, 60, 80.0) == 0.0


# ---------------------------------------------------------------------------
# Wochenvolumen
# ---------------------------------------------------------------------------

def _satz(db, workout, uebung, wdh=10, gewicht=None, rpe=None, nummer=1):
    s = WorkoutSet(workout_id=workout.id, exercise_id=uebung.id,
                   set_number=nummer, weight_kg=gewicht, reps=wdh, rpe=rpe,
                   is_completed=True, is_warmup=False, set_type="normal")
    db.add(s)
    return s


def test_woche_zaehlt_direkte_und_gewichtete_saetze(db_session, klimmzug):
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    for i in range(3):
        _satz(db_session, w, klimmzug, nummer=i + 1)
    db_session.commit()

    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    # Latissimus ist mit 1.0 dabei: drei direkte Saetze.
    assert ergebnis["latissimus"].direkt == 3.0
    assert ergebnis["latissimus"].gewichtet == 3.0
    # Bizeps mit 0.6: zaehlt direkt mit (Schwelle 0.6) ...
    assert ergebnis["bizeps"].direkt == 3.0
    # ... Unterarm mit 0.5 nur gewichtet.
    assert ergebnis["unterarm"].direkt == 0.0
    assert ergebnis["unterarm"].gewichtet == 1.5


def test_niedriger_rpe_zaehlt_nicht_als_reiz(db_session, klimmzug):
    """RPE 2 heißt acht Wiederholungen im Tank. Das ist Aufwärmen, kein Reiz."""
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    _satz(db_session, w, klimmzug, rpe=2.0)
    db_session.commit()

    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    assert ergebnis["latissimus"].direkt == 0.0


def test_fehlender_rpe_zaehlt_mit(db_session, klimmzug):
    """Die nachsichtige Richtung, absichtlich: die meisten Sätze werden ohne
    RPE eingetragen, und ein Zähler, der die verwirft, meldet dauerhaft zu
    wenig Volumen."""
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    _satz(db_session, w, klimmzug, rpe=None)
    db_session.commit()

    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    assert ergebnis["latissimus"].direkt == 1.0


def test_bewertung_trifft_die_landmarks(db_session, klimmzug):
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    # Latissimus: mev 10, mav 14 bis 22, mrv 25.
    for i in range(16):
        _satz(db_session, w, klimmzug, nummer=i + 1)
    db_session.commit()

    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    assert ergebnis["latissimus"].direkt == 16.0
    assert ergebnis["latissimus"].bewertung == "im_korridor"


def test_bewertung_ueber_mrv(db_session, klimmzug):
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    for i in range(30):
        _satz(db_session, w, klimmzug, nummer=i + 1)
    db_session.commit()

    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    assert ergebnis["latissimus"].bewertung == "ueber_mrv"


def test_gruppe_ohne_mev_wird_nicht_als_baustelle_gemeldet(db_session):
    """Die vordere Schulter hat MEV 0: sie bekommt bei jedem Drücken genug ab."""
    ergebnis = {g.gruppe: g for g in VolumenService(db_session, 80.0).woche()}
    assert ergebnis["front_delta"].bewertung == "erhaltung"
    assert "0 Sätze wären" not in ergebnis["front_delta"].hinweis


# ---------------------------------------------------------------------------
# Frische
# ---------------------------------------------------------------------------

def test_frische_ist_voll_ohne_training(db_session):
    werte = {f.gruppe: f for f in VolumenService(db_session, 80.0).frische()}
    assert werte["brust"].frische == 1.0
    assert werte["brust"].stunden_seit is None


def test_frische_faellt_nach_belastung(db_session, klimmzug):
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    for i in range(6):
        _satz(db_session, w, klimmzug, nummer=i + 1)
    db_session.commit()

    werte = {f.gruppe: f for f in VolumenService(db_session, 80.0).frische()}
    assert werte["latissimus"].frische < 0.5
    assert werte["latissimus"].bereit_in_stunden > 0
    # Eine unbeteiligte Gruppe bleibt frisch.
    assert werte["quadrizeps"].frische == 1.0


def test_frische_erholt_sich_mit_der_zeit(db_session, klimmzug):
    """Dieselbe Belastung, aber vier Tage her."""
    alt = datetime.now(timezone.utc) - timedelta(days=4)
    w = Workout(name="Test", started_at=alt)
    db_session.add(w)
    db_session.flush()
    for i in range(6):
        _satz(db_session, w, klimmzug, nummer=i + 1)
    db_session.commit()

    werte = {f.gruppe: f for f in VolumenService(db_session, 80.0).frische()}
    assert werte["latissimus"].frische > 0.85


def test_je_muskel_unterscheidet_die_koepfe(db_session, klimmzug):
    """★ Der Grund für die Muskelebene: Latissimus und Bizeps werden vom
    selben Satz unterschiedlich stark getroffen."""
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    _satz(db_session, w, klimmzug)
    db_session.commit()

    werte = VolumenService(db_session, 80.0).je_muskel()
    assert werte["latissimus"]["saetze"] == 1.0
    assert werte["bizeps_lang"]["saetze"] == 0.6
    assert werte["unterarm_beuger"]["saetze"] == 0.5
    assert werte["latissimus"]["tage_seit"] == 0
    assert werte["quadrizeps"]["saetze"] == 0.0 if "quadrizeps" in werte else True
    assert werte["rectus_femoris"]["tage_seit"] is None
