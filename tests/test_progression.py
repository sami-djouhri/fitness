"""1RM-Schaetzung, Doppelprogression, Plateau-Erkennung, Rundung."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Exercise, Workout, WorkoutSet
from app.services.progression import (
    ProgressionsService, brzycki, epley, geschaetztes_1rm, gewicht_fuer_wdh,
    lombardi, rir_aus_rpe, runden_auf_schritt,
)


@pytest.fixture
def bankdruecken(db_session):
    ex = Exercise(name="Bankdrücken Test", category="Brust",
                  equipment="Langhantel", is_compound=True,
                  wdh_min=6, wdh_max=10, pause_s=150)
    ex.muskel_anteile = {"brust_mitte": 1.0, "trizeps_lateral": 0.6}
    db_session.add(ex)
    db_session.commit()
    return ex


@pytest.fixture
def liegestuetz(db_session):
    ex = Exercise(name="Liegestütze Test", category="Brust",
                  equipment="Körpergewicht", kg_anteil=0.64,
                  reihe="liegestuetz-test", stufe=3, wdh_min=8, wdh_max=20)
    ex.muskel_anteile = {"brust_mitte": 1.0}
    schwerer = Exercise(name="Archer-Liegestütze Test", category="Brust",
                        equipment="Körpergewicht", kg_anteil=0.80,
                        reihe="liegestuetz-test", stufe=4, wdh_min=4, wdh_max=10)
    schwerer.muskel_anteile = {"brust_mitte": 1.0}
    db_session.add_all([ex, schwerer])
    db_session.commit()
    return ex


def _einheit(db, uebung, saetze, wann=None, rpe=None):
    """Legt eine Einheit an. ``saetze`` ist eine Liste (gewicht, wdh)."""
    w = Workout(name="Test", started_at=wann or datetime.now(timezone.utc))
    db.add(w)
    db.flush()
    for i, (gewicht, wdh) in enumerate(saetze):
        db.add(WorkoutSet(workout_id=w.id, exercise_id=uebung.id,
                          set_number=i + 1, weight_kg=gewicht, reps=wdh,
                          rpe=rpe, is_completed=True, is_warmup=False,
                          set_type="normal"))
    db.commit()
    return w


# ---------------------------------------------------------------------------
# 1RM
# ---------------------------------------------------------------------------

def test_eine_wiederholung_ist_das_1rm():
    wert, unsicher = geschaetztes_1rm(100, 1)
    assert wert == 100.0
    assert not unsicher


def test_median_liegt_zwischen_den_formeln():
    """★ Der Bestand nutzte allein Epley, das oberhalb von zehn
    Wiederholungen deutlich überschätzt."""
    wert, _ = geschaetztes_1rm(100, 10)
    werte = sorted([epley(100, 10), brzycki(100, 10), lombardi(100, 10)])
    assert werte[0] <= wert <= werte[-1]
    assert wert == pytest.approx(werte[1], abs=0.1)


def test_hohe_wiederholungszahl_wird_als_unsicher_gemeldet():
    _wert, unsicher = geschaetztes_1rm(50, 20)
    assert unsicher
    _wert, unsicher = geschaetztes_1rm(100, 5)
    assert not unsicher


def test_ohne_gewicht_kein_1rm():
    assert geschaetztes_1rm(None, 10) == (None, False)
    assert geschaetztes_1rm(100, None) == (None, False)
    assert geschaetztes_1rm(0, 10) == (None, False)


def test_brzycki_bricht_bei_sehr_vielen_wiederholungen_nicht_aus():
    """Der Nenner wird ab 37 Wiederholungen negativ. Ohne Abfangen käme ein
    negatives 1RM heraus, und der Median wäre still falsch."""
    assert brzycki(50, 40) == 0.0
    wert, _ = geschaetztes_1rm(50, 40)
    assert wert is not None and wert > 50


def test_gewicht_fuer_wdh_ist_die_umkehrung():
    e1rm = 100.0
    gewicht = gewicht_fuer_wdh(e1rm, 10)
    zurueck = epley(gewicht, 10)
    assert zurueck == pytest.approx(e1rm, abs=0.5)


def test_rir_aus_rpe():
    assert rir_aus_rpe(10) == 0.0
    assert rir_aus_rpe(8) == 2.0
    assert rir_aus_rpe(None) is None


# ---------------------------------------------------------------------------
# Rundung
# ---------------------------------------------------------------------------

def test_rundung_auf_den_moeglichen_schritt():
    """★ Ein Vorschlag von 22,5 kg ist wertlos, wenn die verstellbare
    Kurzhantel in 2-kg-Stufen geht."""
    assert runden_auf_schritt(22.5, 2.0) == 22.0
    assert runden_auf_schritt(23.5, 2.0) == 24.0
    assert runden_auf_schritt(22.5, 2.5) == 22.5
    assert runden_auf_schritt(51.2, 5.0) == 50.0


def test_rundung_mit_schritt_null_bricht_nicht():
    assert runden_auf_schritt(22.5, 0) == 22.5


# ---------------------------------------------------------------------------
# Vorschlag
# ---------------------------------------------------------------------------

def test_ohne_historie_kommt_ein_einstieg(db_session, bankdruecken):
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "einstieg"
    assert v.gewicht_kg is None
    assert "Noch nichts erfasst" in v.begruendung


def test_oberes_ende_erreicht_erhoeht_das_gewicht(db_session, bankdruecken):
    _einheit(db_session, bankdruecken, [(60, 10), (60, 10), (60, 10)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "steigern"
    assert v.gewicht_kg == 62.5


def test_gewichtsschritt_des_profils_wird_benutzt(db_session, bankdruecken):
    _einheit(db_session, bankdruecken, [(60, 10), (60, 10), (60, 10)])
    svc = ProgressionsService(db_session, 2.0, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.gewicht_kg == 62.0


def test_mitten_im_bereich_steigert_die_wiederholungen(db_session, bankdruecken):
    _einheit(db_session, bankdruecken, [(60, 7), (60, 7), (60, 7)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "wdh_steigern"
    assert v.gewicht_kg == 60
    assert v.wdh == 8


def test_viel_reserve_erlaubt_zwei_wiederholungen_mehr(db_session, bankdruecken):
    _einheit(db_session, bankdruecken, [(60, 7)], rpe=6.0)   # RIR 4
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.wdh == 9
    assert "noch" in v.begruendung


def test_unter_dem_zielbereich_wird_reduziert(db_session, bankdruecken):
    _einheit(db_session, bankdruecken, [(80, 4)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "reduzieren"
    assert v.gewicht_kg == 77.5


def test_oberes_ende_ohne_reserve_wiederholt_das_gewicht(db_session, bankdruecken):
    """RIR 0 heißt: nichts mehr im Tank. Mehr Gewicht drückt die nächste
    Einheit unter den Zielbereich."""
    _einheit(db_session, bankdruecken, [(60, 10), (60, 10)], rpe=10.0)
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "wiederholen"
    assert v.gewicht_kg == 60


def test_plateau_wird_erkannt(db_session, bankdruecken):
    """Drei Einheiten ohne Zuwachs im geschätzten 1RM."""
    jetzt = datetime.now(timezone.utc)
    for tage in (12, 9, 6, 3):
        _einheit(db_session, bankdruecken, [(60, 8)],
                 wann=jetzt - timedelta(days=tage))
    svc = ProgressionsService(db_session, 2.5, 80.0)
    assert svc.plateau_laenge(bankdruecken.id) >= 3
    v = svc.vorschlag(bankdruecken.id)
    assert v.art == "plateau"
    assert "kein Zuwachs" in v.begruendung


def test_steigerung_beendet_das_plateau(db_session, bankdruecken):
    jetzt = datetime.now(timezone.utc)
    for tage, gewicht in ((12, 60), (9, 60), (6, 60), (3, 65)):
        _einheit(db_session, bankdruecken, [(gewicht, 8)],
                 wann=jetzt - timedelta(days=tage))
    svc = ProgressionsService(db_session, 2.5, 80.0)
    assert svc.plateau_laenge(bankdruecken.id) == 0


# ---------------------------------------------------------------------------
# Koerpergewichtsuebungen
# ---------------------------------------------------------------------------

def test_koerpergewicht_steigert_erst_die_wiederholungen(db_session, liegestuetz):
    _einheit(db_session, liegestuetz, [(None, 12), (None, 12)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(liegestuetz.id)
    assert v.art == "wdh_steigern"
    assert v.wdh == 13


def test_am_oberen_ende_kommt_die_naechste_stufe(db_session, liegestuetz):
    """★ Nicht "mach halt mehr", sondern die schwerere Variante derselben
    Reihe."""
    _einheit(db_session, liegestuetz, [(None, 20), (None, 20)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(liegestuetz.id)
    assert v.art == "steigern"
    assert "Archer-Liegestütze Test" in v.begruendung


def test_ohne_naechste_stufe_kommt_zusatzgewicht(db_session):
    ex = Exercise(name="Dips Test", category="Brust", equipment="Körpergewicht",
                  kg_anteil=1.0, wdh_min=5, wdh_max=15)
    ex.muskel_anteile = {"brust_unten": 1.0}
    db_session.add(ex)
    db_session.commit()
    _einheit(db_session, ex, [(None, 15), (None, 15)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(ex.id)
    assert v.art == "steigern"
    assert v.gewicht_kg == 2.5
    assert "Rucksack" in v.begruendung


def test_zeitbasierte_uebung_steigert_sekunden(db_session):
    ex = Exercise(name="Plank Test", category="Rumpf", equipment="Körpergewicht",
                  kg_anteil=0.55, ist_zeit=True, wdh_min=20, wdh_max=120)
    ex.muskel_anteile = {"transversus": 1.0}
    db_session.add(ex)
    db_session.commit()
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db_session.add(w)
    db_session.flush()
    db_session.add(WorkoutSet(workout_id=w.id, exercise_id=ex.id, set_number=1,
                              duration_seconds=45, is_completed=True,
                              is_warmup=False, set_type="normal"))
    db_session.commit()
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(ex.id)
    assert v.art == "wdh_steigern"
    assert "50" in v.begruendung


# ---------------------------------------------------------------------------
# Aufwaermen
# ---------------------------------------------------------------------------

def test_aufwaermsaetze_staffeln_nach_oben(db_session, bankdruecken):
    svc = ProgressionsService(db_session, 2.5, 80.0)
    saetze = svc.aufwaermen(bankdruecken.id, 100)
    assert len(saetze) == 3
    gewichte = [s["gewicht_kg"] for s in saetze]
    assert gewichte == sorted(gewichte)
    assert gewichte[-1] == 80.0


def test_leichtes_arbeitsgewicht_braucht_kein_aufwaermen(db_session, bankdruecken):
    svc = ProgressionsService(db_session, 2.5, 80.0)
    assert svc.aufwaermen(bankdruecken.id, 12) == []


# ---------------------------------------------------------------------------
# Zielbereich
# ---------------------------------------------------------------------------

def test_zielbereich_kommt_aus_dem_katalog_nicht_aus_einer_festen_zwoelf(
        db_session, bankdruecken):
    """★ Die alte Logik verglich jede Übung mit einer eingebauten 12.
    Bei einer Übung mit Zielbereich 6 bis 10 wurde deshalb nie erhöht."""
    _einheit(db_session, bankdruecken, [(60, 10), (60, 10)])
    svc = ProgressionsService(db_session, 2.5, 80.0)
    v = svc.vorschlag(bankdruecken.id)
    assert v.zielbereich == (6, 10)
    assert v.art == "steigern"
