"""Was man zum Trainieren braucht, und was davon jemand tatsaechlich hat.

Der Befund, der dieses Modul ausgeloest hat: die Empfehlungslogik schlug
Beinpresse, Latzug und Kabelzug-Crossover vor, und der aktive Trainingsplan
bestand zu zwei Dritteln aus Langhantel- und Maschinenuebungen. Wer zu Hause
mit Kurzhanteln und einer Klimmzugstange trainiert, kann davon nichts
gebrauchen. Die App wusste schlicht nicht, was da ist: das Feld ``equipment``
am Katalog war eine Anzeigekategorie und wurde nirgends gegen einen Bestand
geprueft.

Zwei Begriffe, die man auseinanderhalten muss:

``equipment``
    Die eine Kategorie, unter der eine Uebung im Katalog gefuehrt wird
    ("Kurzhantel"). Fuer Filter und Anzeige. Bleibt, wie sie war.

``benoetigt``
    Die Menge der Gegenstaende, ohne die die Uebung nicht geht. Klimmzuege
    stehen unter "Körpergewicht" und brauchen trotzdem eine Stange. Genau
    dieser Unterschied fehlte, und deshalb galt jede Klimmzug-Variante als
    ueberall machbar.

★ Was jeder hat, steht in ``IMMER_VORHANDEN`` und wird nie abgefragt. Boden,
Wand und ein Stuhl sind keine Ausruestung, ueber die man Buch fuehrt. Ohne
diese Liste muesste ein Selbsthoster beim ersten Start zwanzig Haken setzen,
bevor ihm eine einzige Liegestuetze angeboten wird.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Geraet:
    id: str
    name: str
    # Womit man es ersetzen kann, wenn es fehlt. Die App nennt das bei einer
    # Uebung, die knapp nicht machbar ist, statt sie wortlos wegzulassen.
    ersatz: tuple[str, ...] = ()
    hinweis: str = ""


# Gegenstaende, die in jeder Wohnung stehen. Nicht abfragbar, immer gesetzt.
IMMER_VORHANDEN: frozenset[str] = frozenset({
    "koerpergewicht", "boden", "wand", "stuhl", "handtuch", "tuerrahmen",
})

GERAETE: dict[str, Geraet] = {g.id: g for g in [
    # --- braucht niemand zu besitzen ---
    Geraet("koerpergewicht", "Körpergewicht"),
    Geraet("boden", "Boden oder Matte"),
    Geraet("wand", "Wand"),
    Geraet("stuhl", "Stuhl oder Sofakante"),
    Geraet("handtuch", "Handtuch"),
    Geraet("tuerrahmen", "Türrahmen"),

    # --- Heim-Grundausstattung ---
    Geraet("kurzhantel", "Kurzhanteln",
           ersatz=("kettlebell", "band", "rucksack"),
           hinweis="Ein gefüllter Rucksack ersetzt sie für viele Übungen."),
    Geraet("klimmzugstange", "Klimmzugstange",
           ersatz=("schlingentrainer",),
           hinweis="Ohne Stange bleiben Rudern am Tisch und Bandzüge."),
    Geraet("band", "Widerstandsbänder",
           ersatz=("kabelzug",)),
    Geraet("kettlebell", "Kettlebell",
           ersatz=("kurzhantel",)),
    Geraet("bank", "Hantelbank",
           ersatz=("boden", "stuhl"),
           hinweis="Auf dem Boden geht dieselbe Übung mit kürzerem Weg."),
    Geraet("schraegbank", "Schrägbank",
           ersatz=("bank",)),
    Geraet("dip_barren", "Dip-Barren",
           ersatz=("stuhl",),
           hinweis="Zwei stabile Stuhllehnen tun es auch."),
    Geraet("schlingentrainer", "Schlingentrainer",
           ersatz=("klimmzugstange", "band")),
    Geraet("rucksack", "Rucksack als Zusatzgewicht"),
    Geraet("gewichtsweste", "Gewichtsweste",
           ersatz=("rucksack", "dipguertel")),
    Geraet("dipguertel", "Dipgürtel",
           ersatz=("rucksack", "gewichtsweste")),
    Geraet("ab_rad", "Bauchroller",
           ersatz=("handtuch",),
           hinweis="Auf glattem Boden geht es mit einem Handtuch unter den Händen."),
    Geraet("springseil", "Springseil"),
    Geraet("faszienrolle", "Faszienrolle"),

    # --- Studio ---
    Geraet("langhantel", "Langhantel",
           ersatz=("kurzhantel",)),
    Geraet("rack", "Squat-Rack oder Ständer"),
    Geraet("kabelzug", "Kabelzug",
           ersatz=("band",),
           hinweis="Ein Band am Türanker ersetzt fast jeden Kabelzug."),
    Geraet("latzug", "Latzugmaschine",
           ersatz=("klimmzugstange", "band")),
    Geraet("beinpresse", "Beinpresse"),
    Geraet("beinstrecker", "Beinstreckermaschine"),
    Geraet("beinbeuger", "Beinbeugermaschine"),
    Geraet("rudermaschine_kabel", "Rudermaschine am Kabel",
           ersatz=("kurzhantel", "band")),
    Geraet("wadenmaschine", "Wadenmaschine",
           ersatz=("kurzhantel",)),
    Geraet("butterfly", "Butterfly-Maschine",
           ersatz=("kurzhantel", "kabelzug")),
    Geraet("beinheben_station", "Beinheben-Station",
           ersatz=("klimmzugstange",)),
    Geraet("hyperextension", "Rückenstrecker-Bank",
           ersatz=("boden",)),

    # --- Ausdauer ---
    Geraet("laufband", "Laufband"),
    Geraet("ergometer", "Fahrradergometer"),
    Geraet("rudergeraet", "Rudergerät"),
    Geraet("crosstrainer", "Crosstrainer"),
]}


# Vorbelegungen, damit die Einrichtung ein Tippen ist und keine Liste von
# dreissig Haken. Der Nutzer waehlt eine und feilt danach nach.
VORLAGEN: dict[str, dict] = {
    "koerpergewicht": {
        "name": "Nur Körpergewicht",
        "beschreibung": "Boden, Wand, Stuhl. Kein gekauftes Gerät.",
        "geraete": [],
    },
    "heim_klein": {
        "name": "Kleines Heimstudio",
        "beschreibung": "Kurzhanteln und Klimmzugstange. Deckt den größten Teil ab.",
        "geraete": ["kurzhantel", "klimmzugstange"],
    },
    "heim_gross": {
        "name": "Ausgebautes Heimstudio",
        "beschreibung": "Dazu Bank, Bänder und Zusatzgewicht.",
        "geraete": ["kurzhantel", "klimmzugstange", "bank", "band",
                    "dip_barren", "rucksack", "kettlebell"],
    },
    "studio": {
        "name": "Fitnessstudio",
        "beschreibung": "Alles da, inklusive Maschinen und Kabelzug.",
        "geraete": [g for g in GERAETE if g not in IMMER_VORHANDEN],
    },
}


def geraete_eines_nutzers(gewaehlt: list[str] | None) -> frozenset[str]:
    """Der Bestand eines Nutzers, immer inklusive der Selbstverstaendlichkeiten."""
    return IMMER_VORHANDEN | frozenset(gewaehlt or ())


def machbar(benoetigt: list[str] | None, bestand: frozenset[str]) -> bool:
    """Reicht der Bestand fuer diese Uebung?

    Leere Anforderung heisst machbar: eine Uebung ohne Angabe ist eine
    Koerpergewichtsuebung, und die geht ueberall. Das ist die sichere Seite,
    weil eine faelschlich angebotene Liegestuetze weniger schadet als ein
    stillschweigend leerer Katalog.
    """
    if not benoetigt:
        return True
    return all(g in bestand for g in benoetigt)


def fehlend(benoetigt: list[str] | None, bestand: frozenset[str]) -> list[str]:
    """Was genau fehlt. Fuer die Anzeige "geht dir noch fuer X"."""
    if not benoetigt:
        return []
    return [g for g in benoetigt if g not in bestand]


def mit_ersatz_machbar(benoetigt: list[str] | None,
                       bestand: frozenset[str]) -> tuple[bool, list[str]]:
    """Machbar, wenn man einen Ersatz gelten laesst?

    Rueckgabe: (machbar, Liste der Ersatz-Kennungen, die dafuer noetig waeren).
    Wird fuer den Hinweis "mit Band statt Kabelzug" gebraucht, nicht fuer die
    Vorschlagsliste: dort zaehlt nur der echte Bestand.
    """
    luecken = fehlend(benoetigt, bestand)
    if not luecken:
        return True, []
    ersatzteile: list[str] = []
    for luecke in luecken:
        geraet = GERAETE.get(luecke)
        if not geraet:
            return False, []
        treffer = next((e for e in geraet.ersatz if e in bestand), None)
        if treffer is None:
            return False, []
        ersatzteile.append(treffer)
    return True, ersatzteile


def name(geraet_id: str) -> str:
    g = GERAETE.get(geraet_id)
    return g.name if g else geraet_id
