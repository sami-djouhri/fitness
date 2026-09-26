"""Die Muskel-Registry und der Katalog muessen zueinander passen.

Diese Tests sind Struktur-Tests, keine Verhaltens-Tests: sie pruefen, dass
kein Katalogeintrag auf einen Muskel zeigt, den es nicht gibt, und dass jede
Ebene der Hierarchie geschlossen ist. Ein Tippfehler in einer Muskelkennung
faellt sonst nirgends auf, er laesst die Uebung nur still aus jeder
Auswertung fallen.
"""

from app.data.uebungskatalog import KATALOG
from app.services.ausruestung import (
    GERAETE, IMMER_VORHANDEN, VORLAGEN, fehlend, machbar,
    geraete_eines_nutzers, mit_ersatz_machbar,
)
from app.services.muskulatur import (
    GRUPPEN, MUSKELN, REGIONEN, SAMMEL_ALIAS, muskel_aufloesen,
)


def test_jeder_muskel_haengt_an_einer_bekannten_gruppe():
    for muskel in MUSKELN.values():
        assert muskel.gruppe in GRUPPEN, f"{muskel.id} zeigt auf {muskel.gruppe}"


def test_jede_gruppe_haengt_an_einer_bekannten_region():
    for gruppe in GRUPPEN.values():
        assert gruppe.region in REGIONEN, f"{gruppe.id} zeigt auf {gruppe.region}"


def test_jede_gruppe_hat_mindestens_einen_muskel():
    belegt = {m.gruppe for m in MUSKELN.values()}
    fehlend_ = set(GRUPPEN) - belegt
    assert not fehlend_, f"Gruppen ohne Muskel: {sorted(fehlend_)}"


def test_landmarks_sind_aufsteigend():
    """MV <= MEV <= MAV-Beginn <= MAV-Ende <= MRV.

    Eine verdrehte Reihenfolge macht die Bewertung unerreichbar: liegt MEV
    ueber MAV-Beginn, kann keine Zahl je "im Korridor" landen.
    """
    for g in GRUPPEN.values():
        assert g.mv <= g.mev <= g.mav_min <= g.mav_max <= g.mrv, (
            f"{g.id}: {g.mv}/{g.mev}/{g.mav_min}/{g.mav_max}/{g.mrv}")


def test_katalog_zeigt_nur_auf_bekannte_muskeln():
    for eintrag in KATALOG:
        assert eintrag.muskeln, f"{eintrag.name} hat keine Muskeln"
        for mid, anteil in eintrag.muskeln.items():
            assert mid in MUSKELN, f"{eintrag.name}: unbekannter Muskel {mid}"
            assert 0 < anteil <= 1, f"{eintrag.name}: Anteil {mid}={anteil}"


def test_katalog_zeigt_nur_auf_bekannte_geraete():
    for eintrag in KATALOG:
        for geraet in eintrag.benoetigt:
            assert geraet in GERAETE, f"{eintrag.name}: unbekanntes Gerät {geraet}"


def test_katalognamen_sind_eindeutig():
    namen = [e.name for e in KATALOG]
    doppelt = {n for n in namen if namen.count(n) > 1}
    assert not doppelt, f"Doppelte Namen: {sorted(doppelt)}"


def test_jeder_muskel_kommt_in_mindestens_einer_uebung_vor():
    """Ein Muskel, den keine Uebung trifft, ist im Körpermodell nicht
    auswählbar und waere damit nur Dekoration."""
    getroffen: set[str] = set()
    for eintrag in KATALOG:
        getroffen |= set(eintrag.muskeln)
    fehlend_ = set(MUSKELN) - getroffen
    assert not fehlend_, f"Muskeln ohne Übung: {sorted(fehlend_)}"


def test_progressionsreihen_haben_aufsteigende_stufen_ohne_luecke():
    reihen: dict[str, list[int]] = {}
    for eintrag in KATALOG:
        if eintrag.reihe:
            reihen.setdefault(eintrag.reihe, []).append(eintrag.stufe)
    assert reihen, "Keine Progressionsreihen im Katalog"
    for name, stufen in reihen.items():
        assert min(stufen) == 1, f"Reihe {name} beginnt bei {min(stufen)} statt 1"
        # Keine Luecke: sonst schlaegt die Progression eine Stufe vor, die
        # gedanklich zwei Schritte weiter ist.
        luecken = set(range(1, max(stufen) + 1)) - set(stufen)
        assert not luecken, f"Reihe {name}: Stufen fehlen {sorted(luecken)}"


def test_sammelbegriffe_loesen_auf_bekannte_muskeln_auf():
    for begriff, ziele in SAMMEL_ALIAS.items():
        for mid in ziele:
            assert mid in MUSKELN, f"Sammelbegriff '{begriff}' zeigt auf {mid}"


def test_alte_muskelnamen_loesen_noch_auf():
    """Bestandsdaten und selbst angelegte Uebungen nutzen Freitext."""
    assert muskel_aufloesen("Brust")
    assert muskel_aufloesen("Quadrizeps")
    assert muskel_aufloesen("Latissimus")
    assert muskel_aufloesen("Hintere Schulter") == ["delta_hinten"]
    assert muskel_aufloesen("Gibt es nicht") == []
    assert muskel_aufloesen("") == []


# ---------------------------------------------------------------------------
# Ausruestung
# ---------------------------------------------------------------------------

def test_koerpergewichtsuebung_geht_immer():
    bestand = geraete_eines_nutzers([])
    assert machbar([], bestand)
    assert machbar(["wand"], bestand)
    assert machbar(["stuhl", "boden"], bestand)


def test_klimmzug_braucht_eine_stange():
    """★ Der Kernfall: Klimmzuege stehen unter "Körpergewicht" und galten
    deshalb als ueberall machbar."""
    ohne = geraete_eines_nutzers([])
    mit = geraete_eines_nutzers(["klimmzugstange"])
    assert not machbar(["klimmzugstange"], ohne)
    assert machbar(["klimmzugstange"], mit)
    assert fehlend(["klimmzugstange"], ohne) == ["klimmzugstange"]


def test_ersatz_wird_erkannt():
    mit_band = geraete_eines_nutzers(["band"])
    moeglich, ersatz = mit_ersatz_machbar(["kabelzug"], mit_band)
    assert moeglich
    assert ersatz == ["band"]


def test_ersatz_ohne_passendes_geraet_schlaegt_fehl():
    leer = geraete_eines_nutzers([])
    moeglich, ersatz = mit_ersatz_machbar(["beinpresse"], leer)
    assert not moeglich
    assert ersatz == []


def test_vorlagen_nennen_nur_bekannte_geraete():
    for schluessel, vorlage in VORLAGEN.items():
        for geraet in vorlage["geraete"]:
            assert geraet in GERAETE, f"Vorlage {schluessel}: {geraet}"
            assert geraet not in IMMER_VORHANDEN, (
                f"Vorlage {schluessel} listet {geraet}, das jeder hat")
