"""Das Startgewicht: die erste Zahl, wenn noch keine erfasst ist.

Der Befund, mit dem diese Runde begann: ``/api/training/jetzt`` lieferte zu
**jeder** Uebung ``gewicht_kg: null``, und die Startseite zeigte deshalb "3 x 8"
statt "3 x 8 @ 22 kg". Am Live-Bestand gemessen trug keiner von 38 erfassten
Saetzen ein Gewicht, es war also nie eine kaputte Rechnung, sondern ein
Henne-Ei-Problem: ohne angezeigte Zahl wird keine erfasst, ohne erfasste Zahl
gibt es keine anzuzeigen.

Die drei Tests, die den Altstand widerlegen, sind
``test_einstieg_nennt_ein_gewicht``, ``test_verlauf_ohne_gewicht_gilt_als_einstieg``
und ``test_namensweg_greift_trotz_bindestrich``. Alle drei fallen gegen den
Stand vor dem 2026-10-24.
"""

from datetime import datetime, timezone

import pytest

from app.models import Exercise, Nutzerprofil, Workout, WorkoutSet
from app.services import startgewicht
from app.services.progression import (
    ProgressionsService, abrunden_auf_schritt,
)


# ---------------------------------------------------------------------------
# Vorrichtung
# ---------------------------------------------------------------------------

def _profil(db, **felder) -> Nutzerprofil:
    """Ein eingerichtetes Profil. Die Vorgaben entsprechen dem Live-Konto."""
    werte = dict(koerpergewicht_kg=82.0, erfahrung="fortgeschritten",
                 geschlecht="m", gewichtsschritt_kg=2.0, eingerichtet=True)
    werte.update(felder)
    p = Nutzerprofil(**werte)
    db.add(p)
    db.commit()
    return p


def _uebung(db, name, *, equipment="Kurzhantel", kategorie="Schultern",
            muster="druecken_vertikal", kg_anteil=0.0, ist_zeit=False,
            wdh_min=8, wdh_max=12) -> Exercise:
    ex = Exercise(name=name, category=kategorie, equipment=equipment,
                  kg_anteil=kg_anteil, ist_zeit=ist_zeit, muster=muster,
                  wdh_min=wdh_min, wdh_max=wdh_max, pause_s=90)
    ex.muskel_anteile = {"deltoid_vorne": 1.0}
    db.add(ex)
    db.commit()
    return ex


def _satz(db, uebung, gewicht, wdh, *, abgehakt=True):
    w = Workout(name="Test", started_at=datetime.now(timezone.utc))
    db.add(w)
    db.flush()
    db.add(WorkoutSet(workout_id=w.id, exercise_id=uebung.id, set_number=1,
                      weight_kg=gewicht, reps=wdh, is_completed=abgehakt,
                      is_warmup=False, set_type="normal"))
    db.commit()
    return w


def _dienst(db, profil) -> ProgressionsService:
    return ProgressionsService.fuer_profil(db, profil)


# ---------------------------------------------------------------------------
# Der Kernbefund
# ---------------------------------------------------------------------------

def test_einstieg_nennt_ein_gewicht(db_session):
    """Der Befund dieser Runde. Vorher: ``gewicht_kg is None``.

    Gegen den Stand vor dem 2026-10-24 faellt dieser Test.
    """
    profil = _profil(db_session)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.art == "einstieg"
    assert v.gewicht_kg is not None, "Der Einstieg muss eine Zahl nennen"
    assert v.gewicht_quelle == "geschaetzt"
    # 82 kg mal 0,35 (Kurzhantel-Schulterdruecken, mittlere Stufe) = 28,7 als
    # 1RM je Hand, umgerechnet auf 8 Wiederholungen und auf 2-kg-Schritte
    # gerundet.
    assert v.gewicht_kg == pytest.approx(22.0)
    assert v.e1rm == pytest.approx(28.7, abs=0.1)


def test_geschaetztes_gewicht_ist_als_geschaetzt_erkennbar(db_session):
    """Eine geschaetzte Zahl darf nicht wie eine gemessene aussehen.

    Dieselbe Trennung wie ``minuten_quelle`` in ``jetzt.py``. Ohne sie
    uebernimmt die Oberflaeche eine Schaetzung als Messwert.
    """
    profil = _profil(db_session)
    ex = _uebung(db_session, "Seitheben", muster="seitheben")

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.gewicht_quelle == "geschaetzt"
    assert "Geschätzt" in v.begruendung
    assert "82 kg Körpergewicht" in v.begruendung


def test_erfasstes_gewicht_schlaegt_die_schaetzung(db_session):
    """Sobald ein Satz steht, wird gerechnet und nicht mehr geschaetzt."""
    profil = _profil(db_session)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    _satz(db_session, ex, 30.0, 9)

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.art != "einstieg"
    assert v.gewicht_quelle == "gemessen"
    assert v.gewicht_kg == pytest.approx(30.0)
    assert v.letztes_gewicht_kg == pytest.approx(30.0)


def test_verlauf_ohne_gewicht_gilt_als_einstieg(db_session):
    """Der zweite Defekt, und der leisere von beiden.

    Live gemessen an "Wadenheben stehend": ein abgehakter Arbeitssatz ueber
    12 Wiederholungen **ohne** Gewicht. Der Dienst antwortete mit
    "Gleiches Gewicht, Ziel 13 statt 12" und ``gewicht_kg=None``, also
    "dasselbe Gewicht" wie was. Die Zeile sah aus wie eine fortgesetzte
    Progression und trug keine Zahl.
    """
    profil = _profil(db_session)
    ex = _uebung(db_session, "Wadenheben Test", equipment="Maschine",
                 kategorie="Beine", muster="wade", wdh_min=12, wdh_max=20)
    _satz(db_session, ex, None, 12)

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.art == "einstieg"
    assert v.gewicht_kg is not None
    assert v.gewicht_quelle == "geschaetzt"
    # Der Satz unterscheidet "noch nie gemacht" von "ohne Gewicht notiert",
    # sonst sucht der Nutzer, warum sein Eintrag nicht zaehlt.
    assert "ohne Gewicht notiert" in v.begruendung


# ---------------------------------------------------------------------------
# Was KEINE Zahl bekommt
# ---------------------------------------------------------------------------

def test_koerpergewichtsuebung_bleibt_ohne_gewicht(db_session):
    """Ansage 2026-10-24: "Klimmzüge, Liegestütz usw geht auch
    ohne zusatzgewicht".

    Hier ist das leere Gewichtsfeld richtig und nicht der Defekt. Dieser Test
    haelt fest, dass die Behebung des Einstiegs nicht ueber das Ziel
    hinausschiesst und Koerpergewichtsuebungen eine Zahl aufdraengt.
    """
    profil = _profil(db_session)
    klimmzug = _uebung(db_session, "Klimmzüge Obergriff", equipment="Körpergewicht",
                       kategorie="Rücken", muster="ziehen_vertikal", kg_anteil=1.0)
    liegestuetz = _uebung(db_session, "Liegestütze", equipment="Körpergewicht",
                          kategorie="Brust", muster="druecken_horizontal",
                          kg_anteil=0.64)

    dienst = _dienst(db_session, profil)
    for ex in (klimmzug, liegestuetz):
        v = dienst.vorschlag(ex.id)
        assert v.gewicht_kg is None, f"{ex.name} braucht kein Gewicht"
        assert v.gewicht_quelle == "ohne"
        assert not startgewicht.braucht_aeusseres_gewicht(ex)


def test_dehnung_und_cardio_brauchen_kein_gewicht(db_session):
    """``kg_anteil == 0`` allein reicht als Pruefung nicht.

    Eine Dehnuebung traegt denselben Wert wie eine Hanteluebung, und ohne den
    Kategorie-Filter bekaeme "Weltgrößte Dehnung" ein Zielgewicht.
    """
    profil = _profil(db_session)
    for name, kategorie in (("Dehnung Test", "Dehnung"),
                            ("Hüftkreisen Test", "Mobilität"),
                            ("Laufen Test", "Cardio")):
        ex = _uebung(db_session, name, equipment="Körpergewicht",
                     kategorie=kategorie, muster="dehnen")
        assert not startgewicht.braucht_aeusseres_gewicht(ex)
        assert _dienst(db_session, profil).vorschlag(ex.id).gewicht_kg is None


def test_zugband_bekommt_keine_schaetzung(db_session):
    """Ein Zugband hat keine Kilogramm-Angabe.

    Eine Schaetzung in kg waere dort nicht ungenau, sondern bedeutungslos.
    """
    profil = _profil(db_session)
    ex = _uebung(db_session, "Band-Seitheben Test", equipment="Band",
                 muster="seitheben")

    assert not startgewicht.braucht_aeusseres_gewicht(ex)
    assert _dienst(db_session, profil).vorschlag(ex.id).gewicht_quelle == "ohne"


def test_ohne_koerpergewicht_wird_nicht_geraten(db_session):
    """Jedes Vielfache haengt am Koerpergewicht.

    Eines anzunehmen machte die Zahl nicht unsicherer, sondern unbegruendet,
    und sie saehe genauso aus. Stattdessen sagt die Antwort, was fehlt.
    """
    profil = _profil(db_session, koerpergewicht_kg=None)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.gewicht_kg is None
    assert v.gewicht_quelle == "fehlt", "Gebraucht, aber nicht zu benennen"
    assert "Körpergewicht im Profil" in v.begruendung


def test_ohne_standard_bleibt_die_zahl_aus(db_session):
    """Ein unbekanntes Bewegungsmuster erfindet keinen Wert."""
    profil = _profil(db_session)
    ex = _uebung(db_session, "Etwas Neues Test", muster="gibt-es-nicht")

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.gewicht_kg is None
    assert v.gewicht_quelle == "fehlt"


# ---------------------------------------------------------------------------
# Die Nachschlagewege
# ---------------------------------------------------------------------------

def test_namensweg_greift_trotz_bindestrich(db_session):
    """Der dritte Defekt, und der, der wie Deckung aussah.

    Die Tabelle fuehrte "Kurzhantel Schulterdrücken", der Katalog
    "Kurzhantel-Schulterdrücken". Ein Bindestrich, und der Standard griff
    nicht. Gemeldet wurde nichts: ``dict.get`` liefert beim Fehlgriff
    dasselbe wie bei einer Uebung ohne Standard.
    """
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    mit_leerzeichen = _uebung(db_session, "Kurzhantel Schulterdrücken")

    for variante in (ex, mit_leerzeichen):
        stufen = startgewicht.stufentabelle(variante)
        assert stufen, f"{variante.name} findet seinen Standard nicht"
        assert stufen["intermediate"] == pytest.approx(0.35)


def test_alias_fuehrt_die_klimmzug_varianten_zusammen(db_session):
    """Acht Klimmzug-Varianten im Katalog, ein Standard."""
    ex = _uebung(db_session, "Klimmzüge Untergriff", equipment="Körpergewicht",
                 kategorie="Rücken", muster="ziehen_vertikal", kg_anteil=1.0)

    assert startgewicht.stufentabelle(ex)["intermediate"] == pytest.approx(1.0)


def test_musterweg_deckt_was_der_namensweg_nicht_kennt(db_session):
    """Ohne diesen Weg haette die Behebung nichts geaendert.

    Gemessen am 2026-10-24: von 33 Uebungen, die mit Kurzhanteln und
    Klimmzugstange machbar sind und aeusseres Gewicht brauchen, trug
    **keine** einen Namensstandard. Ein Namensweg allein waere eine Loesung
    gewesen, die am Live-Konto genau nichts bewirkt.
    """
    profil = _profil(db_session)
    ex = _uebung(db_session, "Trizeps-Kickbacks", kategorie="Arme",
                 muster="armstrecken")

    assert not startgewicht.stufentabelle(ex), "Kein Namensstandard erwartet"
    schaetzung = startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                                        erfahrung="fortgeschritten", geschlecht="m")
    assert schaetzung is not None
    assert schaetzung.quelle == "musterstandard"
    assert _dienst(db_session, profil).vorschlag(ex.id).gewicht_kg is not None


def test_name_schlaegt_muster(db_session):
    """Goblet-Kniebeugen werden mit EINER Hantel in beiden Haenden gehalten.

    Der Musterweg rechnet Kurzhanteln pro Hand und wuerde hier etwa das
    Doppelte vorschlagen. Deshalb gewinnt der genauere Namenseintrag.
    """
    goblet = _uebung(db_session, "Goblet-Kniebeugen", kategorie="Beine",
                     muster="beugen_knie")
    anderes = _uebung(db_session, "Kurzhantel-Kniebeugen Test", kategorie="Beine",
                      muster="beugen_knie")

    nach_name = startgewicht.schaetzen(goblet, koerpergewicht_kg=82.0,
                                       erfahrung="fortgeschritten", geschlecht="m")
    nach_muster = startgewicht.schaetzen(anderes, koerpergewicht_kg=82.0,
                                         erfahrung="fortgeschritten", geschlecht="m")
    assert nach_name.quelle == "uebungsstandard"
    assert nach_muster.quelle == "musterstandard"
    assert nach_name.e1rm_kg > nach_muster.e1rm_kg


def test_kurzhantel_gilt_pro_hand(db_session):
    """Die Haelfte-oder-nicht-Frage, bei der ein Fehler Faktor zwei kostet.

    Der Kurzhantelwert liegt bei knapp unter der Haelfte des
    Langhantelwerts, weil er je Hand gilt. Wer ihn als Gesamtgewicht liest,
    schlaegt das Doppelte vor.
    """
    langhantel = _uebung(db_session, "Bankdrücken", equipment="Langhantel",
                         kategorie="Brust", muster="druecken_horizontal")
    kurzhantel = _uebung(db_session, "Kurzhantel-Bankdrücken", equipment="Kurzhantel",
                         kategorie="Brust", muster="druecken_horizontal")

    lh = startgewicht.schaetzen(langhantel, koerpergewicht_kg=82.0,
                                erfahrung="fortgeschritten", geschlecht="m")
    kh = startgewicht.schaetzen(kurzhantel, koerpergewicht_kg=82.0,
                                erfahrung="fortgeschritten", geschlecht="m")
    assert kh.e1rm_kg == pytest.approx(lh.e1rm_kg * 0.45, rel=0.01)


def test_pro_hand_steht_im_satz(db_session):
    """Eine Zahl ohne diese Angabe ist im Gym nicht benutzbar."""
    profil = _profil(db_session)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    v = _dienst(db_session, profil).vorschlag(ex.id)
    assert "pro Hand" in v.begruendung

    maschine = _uebung(db_session, "Beinstrecker Test", equipment="Maschine",
                       kategorie="Beine", muster="beugen_knie")
    assert "pro Hand" not in _dienst(db_session, profil).vorschlag(maschine.id).begruendung


# ---------------------------------------------------------------------------
# Stufe, Geschlecht, Ausruestung
# ---------------------------------------------------------------------------

def test_fortgeschritten_ist_die_mittlere_stufe(db_session):
    """Das Wort klingt nach "advanced" und ist die Mitte von drei.

    Eine Verwechslung verschiebt jeden Vorschlag um eine ganze Stufe, beim
    Druecken von 0,35 auf 0,55 des Koerpergewichts.
    """
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    werte = {
        stufe: startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                                      erfahrung=stufe, geschlecht="m").e1rm_kg
        for stufe in ("einsteiger", "fortgeschritten", "erfahren")
    }
    assert werte["einsteiger"] < werte["fortgeschritten"] < werte["erfahren"]
    assert startgewicht.schaetzen(
        ex, koerpergewicht_kg=82.0, erfahrung="fortgeschritten",
        geschlecht="m").stufe == "intermediate"


def test_unbekannte_stufe_nimmt_die_mitte(db_session):
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    s = startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                               erfahrung="gibt-es-nicht", geschlecht="m")
    assert s.stufe == "intermediate"


def test_geschlecht_verschiebt_den_wert(db_session):
    """Dieselben Vielfachen gelten nicht fuer alle.

    ``keine_angabe`` nimmt bewusst die Mitte: der Maennerwert waere fuer etwa
    die Haelfte der Nutzer zu hoch, und ein zu schwerer erster Satz ist der
    teurere Fehler.
    """
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")
    werte = {
        g: startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                                  erfahrung="fortgeschritten", geschlecht=g).e1rm_kg
        for g in ("m", "w", "keine_angabe")
    }
    assert werte["w"] < werte["keine_angabe"] < werte["m"]


def test_oberkoerper_trennt_sich_vom_unterkoerper(db_session):
    """Der Unterschied ist oben deutlich groesser als unten."""
    oben = _uebung(db_session, "Druecken Test", kategorie="Schultern",
                   muster="druecken_vertikal")
    unten = _uebung(db_session, "Beine Test", kategorie="Beine",
                    muster="beugen_knie")

    def anteil(ex):
        m = startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                                   erfahrung="fortgeschritten", geschlecht="m")
        w = startgewicht.schaetzen(ex, koerpergewicht_kg=82.0,
                                   erfahrung="fortgeschritten", geschlecht="w")
        return w.e1rm_kg / m.e1rm_kg

    assert anteil(oben) < anteil(unten)


def test_vorschlag_haelt_sich_an_den_gewichtsschritt(db_session):
    """Ein Vorschlag von 22,5 kg ist wertlos, wenn die Hantel 2-kg-Stufen hat."""
    profil = _profil(db_session, gewichtsschritt_kg=5.0)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")

    gewicht = _dienst(db_session, profil).vorschlag(ex.id).gewicht_kg

    assert gewicht % 5.0 == pytest.approx(0.0)


def test_schwerste_kurzhantel_deckelt_den_vorschlag(db_session):
    """Haelt die Zusage, die im Profil neben dem Feld steht.

    Das Feld ``kurzhantel_max_kg`` wurde bis zum 2026-10-24 gespeichert und
    nirgends gelesen.
    """
    profil = _profil(db_session, kurzhantel_max_kg=12.0)
    ex = _uebung(db_session, "Kurzhantel-Schulterdrücken")

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.gewicht_kg <= 12.0
    assert "schwerste Kurzhantel" in v.begruendung


def test_deckel_wird_nie_nach_oben_gerundet(db_session):
    """Sonst steht ueber dem Deckel ein Gewicht, das es nicht gibt.

    20 kg Deckel mit 2,5-kg-Schritten: aufgerundet waere 21,25 zu 22,5
    geworden, also genau der Wert, den der Deckel verhindern soll.
    """
    assert abrunden_auf_schritt(21.25, 2.5) == pytest.approx(20.0)
    # Und ein genau passender Wert darf nicht um einen Schritt fallen, nur
    # weil 20/2,5 binaer als 7,999... dasteht.
    assert abrunden_auf_schritt(20.0, 2.5) == pytest.approx(20.0)
    assert abrunden_auf_schritt(20.0, 0) == pytest.approx(20.0)


def test_deckel_gilt_nur_fuer_kurzhanteln(db_session):
    """An der Maschine sagt die schwerste Kurzhantel nichts."""
    profil = _profil(db_session, kurzhantel_max_kg=12.0)
    ex = _uebung(db_session, "Beinstrecker Test", equipment="Maschine",
                 kategorie="Beine", muster="beugen_knie")

    assert _dienst(db_session, profil).vorschlag(ex.id).gewicht_kg > 12.0


def test_vorschlag_faellt_nie_unter_den_kleinsten_sprung(db_session):
    """Unter dem kleinsten Sprung gibt es nichts aufzulegen.

    Ohne diese Grenze rundet eine kleine Schaetzung auf 0 und die Zeile
    stuende wieder ohne Zahl da, also genau beim Ausgangsbefund.
    """
    profil = _profil(db_session, gewichtsschritt_kg=10.0, koerpergewicht_kg=50.0)
    ex = _uebung(db_session, "Reverse Flys Test", kategorie="Schultern",
                 muster="reverse_fly", wdh_min=15, wdh_max=20)

    gewicht = _dienst(db_session, profil).vorschlag(ex.id).gewicht_kg

    assert gewicht == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Randfall im Bestand
# ---------------------------------------------------------------------------

def test_reduzieren_unter_dem_kleinsten_sprung_bleibt_eine_zahl(db_session):
    """Weniger als nichts geht nicht.

    Wer mit 2 kg arbeitet und 2,5-kg-Spruenge hat, bekam hier ``None`` und
    damit dieselbe leere Zeile, um die es in dieser Runde geht.
    """
    profil = _profil(db_session, gewichtsschritt_kg=2.5)
    ex = _uebung(db_session, "Seitheben Klein Test", muster="seitheben",
                 wdh_min=10, wdh_max=15)
    _satz(db_session, ex, 2.0, 4)

    v = _dienst(db_session, profil).vorschlag(ex.id)

    assert v.gewicht_kg == pytest.approx(2.0)
    assert v.gewicht_quelle == "gemessen"
    assert "nicht" in v.begruendung


def test_tabelle_haelt_keine_erklaerungen_fuer_uebungen(db_session):
    """Die Datendatei erklaert sich selbst, in Schluesseln mit Unterstrich.

    Ohne den Filter waere ``_hinweis`` eine Uebung mit einer Zeichenkette
    statt einer Stufentabelle, und der erste Zugriff darauf bricht an einer
    Stelle, die mit Erklaerungstexten nichts zu tun hat.
    """
    daten = startgewicht.tabelle()
    for abschnitt in ("uebungen", "muster", "aliase"):
        assert not [k for k in daten[abschnitt] if k.startswith("_")]
    for name, stufen in daten["uebungen"].items():
        assert isinstance(stufen, dict), f"{name} traegt keine Stufentabelle"
        assert "intermediate" in stufen


def test_jeder_alias_zeigt_auf_einen_vorhandenen_standard():
    """Ein Alias ins Leere greift still daneben."""
    daten = startgewicht.tabelle()
    for katalogname, standardname in daten["aliase"].items():
        assert standardname in daten["uebungen"], (
            f"Alias {katalogname} zeigt auf {standardname}, das es nicht gibt")
