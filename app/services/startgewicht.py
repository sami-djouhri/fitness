"""Die erste Zahl, wenn noch keine erfasst ist.

Das Problem, das hier geloest wird, ist ein Henne-Ei-Problem und kein Rechenfehler.
``ProgressionsService.vorschlag`` leitet jedes Gewicht aus erfassten Saetzen ab.
Ist zu einer Uebung nichts erfasst, liefert es ``art="einstieg"`` und
``gewicht_kg=None``, also die Zeile "3 x 8" ohne Zahl. Wer im Gym steht, braucht
aber genau die Zahl, und solange keine angezeigt wird, wird auch keine erfasst.
Die Uebung bleibt damit fuer immer im Einstieg.

Am Live-Bestand gemessen (2026-10-24): von 38 erfassten Saetzen trug **kein
einziger** ein Gewicht. Es war also nie ein Fall von "Verlauf vorhanden, Rechnung
kaputt", sondern die Quelle war trocken, seit es den Dienst gibt.

Woraus geschaetzt wird
----------------------

Aus Kraftstandards: dem geschaetzten 1RM als Vielfaches des Koerpergewichts, je
Erfahrungsstufe (``app/data/strength_standards.json``). Alle Angaben dafuer lagen
schon im Haus und waren nur nicht verbunden:

* ``Nutzerprofil.koerpergewicht_kg`` traegt am Modell den Kommentar "Fuer
  Kraftstandards", und bis hierhin benutzte sie keine Kraftstandard-Rechnung.
* ``Nutzerprofil.erfahrung`` und ``geschlecht`` ebenso, letztere woertlich "Nur
  fuer die Kraftstandards".
* ``progression.gewicht_fuer_wdh`` traegt im Docstring "Wird fuer den
  Einstiegsvorschlag gebraucht" und wurde ausserhalb eines Unittests **nie**
  aufgerufen.
* ``strength_standards.json`` lag seit Monaten da und wurde allein fuer die
  Einordnung in ``progress.strength_level`` gelesen.

Der Namensweg allein haette nichts geaendert, und das ist der Teil, der wie
eine Loesung aussieht und keine ist: die Tabelle deckte 14 von 167 Uebungen, alle
mit Langhantel oder Maschine. Beim Bestand des Owners (Kurzhanteln und
Klimmzugstange) sind 33 Uebungen machbar, die aeusseres Gewicht brauchen, und
davon traf der Namensweg **null**. Deshalb gibt es den Musterweg: er haengt an
``Exercise.muster``, das jede Uebung traegt, auch eine selbst angelegte.

Was hier bewusst NICHT passiert
-------------------------------

**Koerpergewichtsuebungen bekommen keine Zahl.** Ansage vom 2026-10-24:
"Klimmzüge, Liegestütz usw geht auch ohne zusatzgewicht". Bei ihnen ist das leere
Gewichtsfeld richtig und nicht der Defekt; ihr Hebel sind Wiederholungen und die
naechste Variante, und den bedient ``vorschlag`` schon.

**Eine Schaetzung wird als Schaetzung ausgewiesen** (``gewicht_quelle``).
Dieselbe Trennung gilt in ``jetzt.py`` fuer die Minuten, mit derselben
Begruendung: eine erfundene Zahl, die wie eine gemessene aussieht, ist der
Fehler, den die Trennung verhindern soll. Der erste erfasste Satz loest die
Schaetzung dauerhaft ab.

**Ohne Koerpergewicht wird nicht geschaetzt.** Jedes Vielfache haengt daran.
Ein angenommenes Koerpergewicht wuerde die Zahl nicht unsicherer machen, sondern
unbegruendet, und sie saehe genauso aus.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.models import Exercise

STANDARD_DATEI = Path(__file__).parent.parent / "data" / "strength_standards.json"

#: Erfahrungsstufe des Profils auf die Stufe der Standardtabelle.
#: ``fortgeschritten`` ist die MITTLERE der drei Profilstufen (siehe
#: ``profil.ERFAHRUNGSFAKTOR``: 0,7 / 1,0 / 1,2) und gehoert deshalb auf
#: ``intermediate``, obwohl das Wort nach "advanced" klingt. Die Verwechslung
#: waere keine Kleinigkeit: sie verschiebt jeden Vorschlag um eine ganze Stufe,
#: beim Druecken etwa von 0,35 auf 0,55 des Koerpergewichts.
STUFEN: dict[str, str] = {
    "einsteiger": "beginner",
    "fortgeschritten": "intermediate",
    "erfahren": "advanced",
}
VORGABE_STUFE = "intermediate"

#: ``equipment`` des Katalogs auf die Geraetefamilie der Mustertabelle.
#: ``Band`` fehlt absichtlich: ein Zugband hat keine Kilogramm-Angabe, eine
#: Schaetzung in kg waere dort nicht ungenau, sondern bedeutungslos.
FAMILIEN: dict[str, str] = {
    "Langhantel": "langhantel",
    "Kurzhantel": "kurzhantel",
    "Maschine": "maschine",
    "Kabelzug": "kabel",
}

#: Kategorien, in denen Gewicht nichts zu suchen hat.
OHNE_GEWICHT = frozenset({"Dehnung", "Mobilität", "Cardio"})

#: Kategorie auf die Haelfte des Koerpers, fuer den Geschlechtsfaktor.
KOERPERHAELFTE: dict[str, str] = {
    "Brust": "oben",
    "Rücken": "oben",
    "Schultern": "oben",
    "Arme": "oben",
    "Beine": "unten",
    "Rumpf": "rumpf",
}


@dataclass
class Schaetzung:
    """Ein geschaetztes 1RM samt der Angabe, worauf es beruht."""

    e1rm_kg: float
    #: ``uebungsstandard`` (Name getroffen) oder ``musterstandard`` (Bewegung).
    quelle: str
    stufe: str
    vielfaches: float
    #: Woran der Wert haengt, in einem Satz und ohne Fachwort.
    grundlage: str


# ---------------------------------------------------------------------------
# Tabelle
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def tabelle() -> dict:
    """Die Standardtabelle, einmal geladen.

    Fehlt oder bricht die Datei, bleibt die Schaetzung aus und der Dienst laeuft
    wie vorher weiter. Ein Vorschlag ohne Zahl ist aermer, aber richtig; ein
    Dienst, der beim Start an einer Datendatei scheitert, ist weg.
    """
    try:
        rohdaten = json.loads(STANDARD_DATEI.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"uebungen": {}, "muster": {}, "aliase": {}, "geschlechtsfaktor": {}}
    return {
        "uebungen": _ohne_hinweise(rohdaten.get("uebungen", {})),
        "muster": _ohne_hinweise(rohdaten.get("muster", {})),
        "aliase": _ohne_hinweise(rohdaten.get("aliase", {})),
        "geschlechtsfaktor": _ohne_hinweise(rohdaten.get("geschlechtsfaktor", {})),
    }


def _ohne_hinweise(abschnitt: dict) -> dict:
    """Erlaeuterungs-Schluessel aus einem Abschnitt werfen.

    Die Datei erklaert sich selbst, und zwar in Schluesseln mit Unterstrich am
    Anfang. Ohne diesen Filter waere ``_hinweis`` ein Uebungsname mit einer
    Zeichenkette statt einer Stufentabelle, und der erste Zugriff darauf
    bricht an einer Stelle, die mit Erklaerungstexten nichts zu tun hat.
    """
    return {k: v for k, v in abschnitt.items() if not k.startswith("_")}


def _schluessel(name: str) -> str:
    """Namen auf eine Form bringen, die Schreibvarianten zusammenfuehrt.

    Genau hier lag einer der Befunde: die Tabelle fuehrte
    ``Kurzhantel Schulterdrücken``, der Katalog ``Kurzhantel-Schulterdrücken``.
    Ein Bindestrich, und der Standard griff nicht. Gemeldet wurde dabei nichts:
    ``dict.get`` liefert bei einem Fehlgriff dasselbe wie bei einer Uebung ohne
    Standard. Die Schluessel heissen jetzt wie der Katalog; diese Faltung ist
    die zweite Sicherung, damit der naechste uebernommene Standard nicht an
    einem Trennzeichen scheitert.

    Die Wortfolge faellt sie nicht zusammen (``Langhantel Bizeps-Curls`` gegen
    ``Bizeps-Curls Langhantel``) -- dafuer gibt es ``aliase``.
    """
    gefaltet = unicodedata.normalize("NFKC", name).casefold()
    return "".join(z for z in gefaltet if z.isalnum())


@lru_cache(maxsize=1)
def _namensindex() -> dict[str, str]:
    """Gefalteter Name auf den Schluessel in ``uebungen``, Aliase eingerechnet."""
    daten = tabelle()
    index = {_schluessel(name): name for name in daten["uebungen"]}
    for katalogname, standardname in daten["aliase"].items():
        if standardname in daten["uebungen"]:
            index[_schluessel(katalogname)] = standardname
    return index


# ---------------------------------------------------------------------------
# Eignung
# ---------------------------------------------------------------------------

def braucht_aeusseres_gewicht(uebung: Exercise) -> bool:
    """Ob diese Uebung ohne eine Gewichtsangabe unvollstaendig ist.

    ``kg_anteil > 0`` heisst Koerpergewichtsuebung und damit NEIN, auch bei
    einer Variante, die Zusatzgewicht vertraegt: Klimmzuege und Liegestuetze
    gehen ohne, ihr leeres Gewichtsfeld ist richtig. Zeit- und
    Dehnungsuebungen ebenso.
    """
    if uebung.ist_zeit or uebung.kg_anteil:
        return False
    if uebung.category in OHNE_GEWICHT:
        return False
    return uebung.equipment in FAMILIEN


def geraetefamilie(uebung: Exercise) -> str | None:
    return FAMILIEN.get(uebung.equipment)


def stufentabelle(uebung: Exercise) -> dict[str, float]:
    """Alle Stufen des Uebungsstandards, oder ein leeres Verzeichnis.

    Fuer die Einordnung in ``progress.strength_level``, die nicht schaetzt,
    sondern einen gemessenen Wert mit den Stufen vergleicht. Bewusst nur der
    Namensweg: "du bist bei Bankdruecken auf Stufe X" ist eine Aussage ueber
    die Uebung, der Musterweg wuerde sie auf eine ganze Bewegungsklasse
    ausdehnen und damit etwas anderes behaupten.
    """
    schluessel = _namensindex().get(_schluessel(uebung.name))
    if not schluessel:
        return {}
    return dict(tabelle()["uebungen"].get(schluessel, {}))


# ---------------------------------------------------------------------------
# Schaetzung
# ---------------------------------------------------------------------------

def _vielfaches(uebung: Exercise, stufe: str) -> tuple[float, str, str] | None:
    """Vielfaches des Koerpergewichts fuer das 1RM, plus Quelle und Grundlage.

    Der Name schlaegt das Muster: ``Goblet-Kniebeugen`` werden mit EINER
    Kurzhantel in beiden Haenden gehalten, der Musterweg wuerde sie wie jede
    andere Kurzhanteluebung pro Hand rechnen und damit etwa das Doppelte
    vorschlagen.
    """
    daten = tabelle()

    schluessel = _namensindex().get(_schluessel(uebung.name))
    if schluessel:
        wert = daten["uebungen"].get(schluessel, {}).get(stufe)
        if wert:
            return float(wert), "uebungsstandard", f"dem Kraftstandard für {schluessel}"

    familie = geraetefamilie(uebung)
    if uebung.muster and familie:
        wert = daten["muster"].get(uebung.muster, {}).get(familie, {}).get(stufe)
        if wert:
            # Kein "pro Hand" in diesem Satzteil: das steht schon an der Zahl
            # selbst, und zweimal im Satz las es sich als zwei Angaben
            # ("8 kg pro Hand ... für diese Bewegung pro Hand").
            return (float(wert), "musterstandard",
                    "dem üblichen Verhältnis für diese Bewegung")
    return None


def _geschlechtsfaktor(uebung: Exercise, geschlecht: str | None) -> float:
    haelfte = KOERPERHAELFTE.get(uebung.category, "oben")
    faktoren = tabelle()["geschlechtsfaktor"].get(haelfte, {})
    return float(faktoren.get(geschlecht or "keine_angabe", 1.0))


def schaetzen(
    uebung: Exercise,
    *,
    koerpergewicht_kg: float | None,
    erfahrung: str | None = None,
    geschlecht: str | None = None,
) -> Schaetzung | None:
    """Geschaetztes 1RM fuer eine Uebung ohne erfassten Verlauf.

    Gibt ``None`` zurueck, wenn nicht geschaetzt werden kann oder soll. Das ist
    ein gueltiges Ergebnis und kein Fehler: besser keine Zahl als eine ohne
    Grundlage.
    """
    if not braucht_aeusseres_gewicht(uebung):
        return None
    if not koerpergewicht_kg or koerpergewicht_kg <= 0:
        return None

    stufe = STUFEN.get(erfahrung or "", VORGABE_STUFE)
    treffer = _vielfaches(uebung, stufe)
    if treffer is None:
        return None
    vielfaches, quelle, grundlage = treffer

    e1rm = float(koerpergewicht_kg) * vielfaches * _geschlechtsfaktor(uebung, geschlecht)
    if e1rm <= 0:
        return None
    return Schaetzung(
        e1rm_kg=round(e1rm, 1),
        quelle=quelle,
        stufe=stufe,
        vielfaches=vielfaches,
        grundlage=grundlage,
    )
