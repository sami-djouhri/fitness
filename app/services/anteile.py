"""Wie stark eine Uebung einen Muskel trifft, und wie schwer sie wirklich ist.

Zwei Rechnungen, die vorher nicht existierten und ohne die die halbe Statistik
falsch war.

**Anteile.** Der Katalog kannte ``primary_muscles`` und
``secondary_muscles``. Beim Zaehlen hiess das entweder "voll" oder "gar nicht",
je nachdem, welche Liste der Aufrufer gerade las. ``muscle_freshness`` zaehlte
beide gleich, ``volume_per_muscle`` nur die primaeren. Dieselbe Uebung ergab
also je nach Ansicht ein anderes Bild. Jetzt traegt jede Katalogeintrag
Anteile zwischen 0 und 1, und es gibt genau eine Stelle, die sie liefert.

**Last.** ★★ ``weight_kg`` ist bei einer Koerpergewichtsuebung leer. Volumen
ist ``Gewicht mal Wiederholungen``, also war das Volumen jedes Klimmzugs und
jeder Liegestuetze **null**. Fuer jemanden, der zu Hause ohne Hanteln
trainiert, war die gesamte Fortschrittsanzeige damit eine Nulllinie, und die
Muskelbilanz zeigte "nie trainiert" fuer Muskeln, die dreimal die Woche
drankamen. Hier wird daraus eine Zahl: Koerpergewicht mal bewegtem Anteil,
plus etwaiges Zusatzgewicht.
"""

from __future__ import annotations

from app.models import Exercise
from app.services.muskulatur import GRUPPEN, MUSKELN, muskel_aufloesen

# Anteil, mit dem ein Muskel aus der alten ``secondary``-Liste gezaehlt wird.
# Entspricht der ueblichen Konvention beim Satzzaehlen: ein Muskel, der
# deutlich mitarbeitet, aber nicht die Zieleinheit ist, geht mit einem halben
# Satz ein.
ANTEIL_SEKUNDAER = 0.5

# Ab hier zaehlt ein Satz fuer diesen Muskel als "harter Satz" im Sinne der
# Volumen-Landmarks. Darunter arbeitet der Muskel mit, aber er ist nicht das
# Ziel des Satzes.
SCHWELLE_HARTER_SATZ = 0.6


def anteile(uebung: Exercise) -> dict[str, float]:
    """Muskelkennung auf Anteil, fuer jede Uebung, auch fuer selbst angelegte.

    Reihenfolge:

    1. Sind gepflegte Anteile da (Katalog seit 2026-09), gelten die.
    2. Sonst werden ``primary``/``secondary`` ueber die Aliastabelle auf
       Kennungen abgebildet. Das betrifft Uebungen, die ein Nutzer selbst
       angelegt hat: dort steht Freitext wie "Brust", und daraus werden die
       drei Anteile des Brustmuskels mit vollem Gewicht.
    3. Was sich nicht abbilden laesst, faellt weg. Ein erfundener Muskelname
       soll die Bilanz nicht verschieben.
    """
    gepflegt = uebung.muskel_anteile
    if gepflegt:
        return {k: float(v) for k, v in gepflegt.items() if k in MUSKELN}

    ergebnis: dict[str, float] = {}
    for name in uebung.primary_muscles:
        for mid in muskel_aufloesen(name):
            ergebnis[mid] = max(ergebnis.get(mid, 0.0), 1.0)
    for name in uebung.secondary_muscles:
        for mid in muskel_aufloesen(name):
            ergebnis[mid] = max(ergebnis.get(mid, 0.0), ANTEIL_SEKUNDAER)
    return ergebnis


def gruppenanteile(uebung: Exercise) -> dict[str, float]:
    """Dasselbe eine Ebene hoeher: Muskelgruppe auf Anteil.

    Eine Gruppe zaehlt mit dem **hoechsten** Anteil ihrer Muskeln, nicht mit
    der Summe. Sonst ergaebe eine Kniebeuge, die vier Quadrizeps-Koepfe mit
    je 1.0 trifft, vier Saetze Quadrizeps statt einem. Genau dieser Fehler
    laesst eine Volumenrechnung um den Faktor der Koepfe danebenliegen.
    """
    ergebnis: dict[str, float] = {}
    for mid, anteil in anteile(uebung).items():
        muskel = MUSKELN.get(mid)
        if not muskel:
            continue
        vorher = ergebnis.get(muskel.gruppe, 0.0)
        if anteil > vorher:
            ergebnis[muskel.gruppe] = anteil
    return ergebnis


def regionenanteile(uebung: Exercise) -> dict[str, float]:
    """Und noch eine Ebene hoeher, fuer die grobe Koerperkarte."""
    ergebnis: dict[str, float] = {}
    for gid, anteil in gruppenanteile(uebung).items():
        gruppe = GRUPPEN.get(gid)
        if not gruppe:
            continue
        vorher = ergebnis.get(gruppe.region, 0.0)
        if anteil > vorher:
            ergebnis[gruppe.region] = anteil
    return ergebnis


def effektive_last(uebung: Exercise, zusatz_kg: float | None,
                   koerpergewicht_kg: float | None) -> float:
    """Was der Muskel tatsaechlich bewegt, in Kilogramm.

    ``zusatz_kg`` ist bei einer Hanteluebung das Hantelgewicht und bei einer
    Koerpergewichtsuebung das, was man sich zusaetzlich umgeschnallt hat. Bei
    einer Klimmzug-Variante mit Rucksack sind also beide Summanden im Spiel.

    Ohne bekanntes Koerpergewicht bleibt nur das Zusatzgewicht uebrig. Das ist
    besser als eine geratene Zahl: ein erfundenes Koerpergewicht wandert sonst
    durch jede Statistik und sieht dort aus wie eine Messung. Die App fragt
    stattdessen einmal danach.
    """
    last = float(zusatz_kg or 0.0)
    if uebung.kg_anteil and koerpergewicht_kg:
        last += float(koerpergewicht_kg) * float(uebung.kg_anteil)
    return round(last, 2)


def satzvolumen(uebung: Exercise, zusatz_kg: float | None, wdh: int | None,
                koerpergewicht_kg: float | None) -> float:
    """Volumen eines Satzes: Last mal Wiederholungen.

    Zeitbasierte Uebungen (Plank, Hang) ergeben bewusst 0. Sekunden mal
    Kilogramm ist keine sinnvolle Groesse und wuerde die Volumenkurve
    verzerren, sobald jemand lange Planks macht. Sie werden ueber die
    Satzzahl erfasst, nicht ueber das Volumen.
    """
    if uebung.ist_zeit:
        return 0.0
    if not wdh:
        return 0.0
    return round(effektive_last(uebung, zusatz_kg, koerpergewicht_kg) * int(wdh), 1)


def ist_harter_satz(anteil: float) -> bool:
    return anteil >= SCHWELLE_HARTER_SATZ
