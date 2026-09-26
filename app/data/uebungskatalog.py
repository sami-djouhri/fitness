"""Der Uebungskatalog als Quelltext, nicht als Datenbankinhalt.

Warum hier und nicht in einer Migration
---------------------------------------

Bis 2026-09 stand der Katalog in ``0001_initial_schema`` und
``0006_seed_stretching_exercises``, also in Wanderungsschritten, die man nicht
noch einmal ausfuehrt. Eine Uebung zu korrigieren hiess damit: eine neue
Migration schreiben. Entsprechend wurde nie eine korrigiert. Jetzt liegt der
Katalog hier, und ``katalog_einspielen`` gleicht ihn bei jedem Start gegen die
Datenbank ab: neue Eintraege kommen dazu, geaenderte Stammdaten werden
nachgezogen, nichts wird geloescht.

Was an einer Uebung dranhaengt
------------------------------

``muskeln``
    Muskelkennung aus ``services/muskulatur.py`` auf einen Anteil zwischen
    0 und 1. Das ist der Unterschied zum alten ``primary``/``secondary``:
    ein Klimmzug traegt den Latissimus mit 1.0 und den Bizeps mit 0.6, und
    genau so wird er in der Wochenrechnung gezaehlt. Die alte Zweiteilung
    zwang dazu, entweder zu viel oder gar nichts zu zaehlen.

``kg_anteil``
    Der Anteil des Koerpergewichts, den die Uebung tatsaechlich bewegt.
    ★★ Ohne dieses Feld erzeugt jede Koerpergewichtsuebung null Volumen,
    weil ``weight_kg`` leer bleibt. Wer zu Hause mit Klimmzuegen und
    Liegestuetzen trainiert, sah in der Statistik bisher eine Nulllinie und
    in der Muskelbilanz nichts. Die Werte stammen aus Kraftmessplatten-
    Untersuchungen zur Liegestuetze (rund 64 Prozent in der oberen, 75 in der
    unteren Position) und sind fuer die uebrigen Uebungen daran anschlussfaehig
    geschaetzt. Sie sind Naeherungen und als solche ausgewiesen, aber eine
    Naeherung schlaegt eine Null.

``muster``
    Bewegungsmuster. Traegt die 3D-Vorfuehrung: animiert wird das Muster,
    nicht die einzelne Uebung. Sonst braeuchte jede der ueber
    zweihundert Uebungen eine eigene Keyframe-Spur, und die letzten fuenfzig
    bekaemen nie eine.

``reihe`` / ``stufe``
    Progressionsreihe fuer Koerpergewichtstraining. Wer keine Klimmzuege
    schafft, bekommt Stufe 2 derselben Reihe vorgeschlagen statt der
    Belehrung, er solle halt Klimmzuege machen.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Katalogeintrag:
    name: str
    kategorie: str
    equipment: str
    muskeln: dict[str, float]
    muster: str
    benoetigt: tuple[str, ...] = ()
    grunduebung: bool = False
    einseitig: bool = False
    kg_anteil: float = 0.0
    griff: str = ""
    reihe: str = ""
    stufe: int = 0
    wdh_min: int = 8
    wdh_max: int = 12
    pause_s: int = 90
    ausfuehrung: str = ""
    fehler: str = ""
    # Zeitbasiert statt wiederholungsbasiert (Plank, Hang, Cardio).
    ist_zeit: bool = False


def _u(name: str, kategorie: str, equipment: str, muskeln: dict[str, float],
       muster: str, **kw) -> Katalogeintrag:
    return Katalogeintrag(name=name, kategorie=kategorie, equipment=equipment,
                          muskeln=muskeln, muster=muster, **kw)


# ===========================================================================
# BRUST
# ===========================================================================

_BRUST = [
    # --- Liegestuetze: die Reihe, die zu Hause traegt ---
    _u("Liegestütze an der Wand", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "trizeps_lateral": 0.4, "trizeps_medial": 0.4,
        "delta_vorne": 0.4, "serratus": 0.3, "bauch_oben": 0.2},
       "druecken_horizontal", benoetigt=("wand",), grunduebung=True,
       kg_anteil=0.20, reihe="liegestuetz", stufe=1,
       wdh_min=10, wdh_max=25, pause_s=60,
       ausfuehrung="Hände schulterbreit an der Wand, Körper in einer Linie, "
                   "Brust zur Wand senken und wegdrücken.",
       fehler="Hüfte knickt ein. Gesäß und Bauch anspannen, dann bleibt die Linie."),
    _u("Liegestütze erhöht", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "brust_unten": 0.5, "trizeps_lateral": 0.5,
        "trizeps_medial": 0.5, "delta_vorne": 0.5, "serratus": 0.3,
        "bauch_oben": 0.3},
       "druecken_horizontal", benoetigt=("stuhl",), grunduebung=True,
       kg_anteil=0.45, reihe="liegestuetz", stufe=2,
       wdh_min=8, wdh_max=20, pause_s=60,
       ausfuehrung="Hände auf Stuhlkante oder Bank, sonst wie die normale Liegestütze. "
                   "Je höher die Hände, desto leichter.",
       fehler="Zu weit vorne aufgestützt. Die Hände gehören unter die Schultern."),
    _u("Liegestütze", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "brust_unten": 0.6, "trizeps_lateral": 0.6,
        "trizeps_medial": 0.6, "delta_vorne": 0.5, "serratus": 0.4,
        "bauch_oben": 0.3, "transversus": 0.3},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.64, reihe="liegestuetz", stufe=3,
       wdh_min=8, wdh_max=20, pause_s=75,
       ausfuehrung="Hände etwas weiter als schulterbreit, Ellenbogen etwa 45 Grad "
                   "am Körper, Brust bis knapp über den Boden.",
       fehler="Ellenbogen rechtwinklig abgespreizt. Das belastet die Schulter "
              "und nimmt der Brust die Arbeit ab."),
    _u("Liegestütze Füße erhöht", "Brust", "Körpergewicht",
       {"brust_oben": 1.0, "brust_mitte": 0.7, "delta_vorne": 0.7,
        "trizeps_lateral": 0.6, "trizeps_medial": 0.6, "serratus": 0.5,
        "bauch_oben": 0.4},
       "druecken_schraeg", benoetigt=("stuhl",), grunduebung=True,
       kg_anteil=0.75, reihe="liegestuetz", stufe=4,
       wdh_min=6, wdh_max=15, pause_s=90,
       ausfuehrung="Füße auf Stuhl oder Bank. Verlagert die Arbeit in die obere Brust "
                   "und die Schulter.",
       fehler="Hohlkreuz, sobald es schwer wird. Lieber weniger Wiederholungen."),
    _u("Diamant-Liegestütze", "Brust", "Körpergewicht",
       {"trizeps_lateral": 1.0, "trizeps_medial": 1.0, "trizeps_lang": 0.7,
        "brust_mitte": 0.7, "delta_vorne": 0.4},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.64, reihe="liegestuetz", stufe=4,
       wdh_min=6, wdh_max=15, pause_s=75,
       ausfuehrung="Daumen und Zeigefinger bilden eine Raute unter der Brust. "
                   "Die stärkste Trizeps-Variante ohne Gerät.",
       fehler="Hände zu weit vorne unter dem Gesicht. Sie gehören unter das Brustbein."),
    _u("Breite Liegestütze", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "brust_unten": 0.7, "delta_vorne": 0.5,
        "trizeps_lateral": 0.3},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.64, reihe="liegestuetz", stufe=3,
       wdh_min=8, wdh_max=18, pause_s=75,
       ausfuehrung="Hände deutlich weiter als schulterbreit. Kürzerer Weg, "
                   "mehr Zug auf der Brust, weniger Trizeps."),
    _u("Archer-Liegestütze", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "trizeps_lateral": 0.6, "delta_vorne": 0.5,
        "bauch_oben": 0.4, "obliquus_extern": 0.4},
       "druecken_horizontal", grunduebung=True, einseitig=True,
       kg_anteil=0.80, reihe="liegestuetz", stufe=5,
       wdh_min=4, wdh_max=10, pause_s=90,
       ausfuehrung="Sehr breite Hände, zu einer Seite absenken, der andere Arm "
                   "bleibt gestreckt. Die Vorstufe zur einarmigen Liegestütze.",
       fehler="Der gestreckte Arm hilft mit. Er soll nur stützen."),
    _u("Einarmige Liegestütze", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "trizeps_lateral": 0.8, "delta_vorne": 0.7,
        "obliquus_extern": 0.7, "bauch_oben": 0.6, "transversus": 0.5},
       "druecken_horizontal", grunduebung=True, einseitig=True,
       kg_anteil=0.95, reihe="liegestuetz", stufe=6,
       wdh_min=1, wdh_max=6, pause_s=150,
       ausfuehrung="Füße weit auseinander, freie Hand am Rücken. Rumpf gegen "
                   "das Verdrehen halten.",
       fehler="Schulter dreht mit ein. Das ist der Punkt, an dem man abbricht."),
    _u("Plyometrische Liegestütze", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "trizeps_lateral": 0.6, "delta_vorne": 0.5},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.70, wdh_min=3, wdh_max=10, pause_s=120,
       ausfuehrung="Explosiv abdrücken, Hände verlassen den Boden. Für Schnellkraft, "
                   "nicht für Volumen."),
    _u("Liegestütze auf Griffen", "Brust", "Körpergewicht",
       {"brust_mitte": 1.0, "brust_unten": 0.6, "trizeps_lateral": 0.6,
        "delta_vorne": 0.5, "serratus": 0.4},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.68, griff="neutral", wdh_min=8, wdh_max=18, pause_s=75,
       ausfuehrung="Griffe oder Kurzhanteln erlauben, tiefer zu gehen als der Boden. "
                   "Mehr Dehnung in der Brust, schonender für die Handgelenke."),
    _u("Krähenstand", "Brust", "Körpergewicht",
       {"delta_vorne": 1.0, "serratus": 0.8, "unterarm_beuger": 0.7,
        "bauch_oben": 0.6, "transversus": 0.6},
       "halten", kg_anteil=0.85, reihe="planche", stufe=1, ist_zeit=True,
       wdh_min=10, wdh_max=60, pause_s=90,
       ausfuehrung="Aus der Hocke die Knie auf die Oberarme legen und das "
                   "Gewicht nach vorne auf die Hände verlagern. Der Einstieg "
                   "in jedes freie Stützen.",
       fehler="Zu wenig nach vorne verlagert. Die Schultern müssen deutlich "
              "vor die Hände."),
    _u("Pseudo-Planche-Liegestütze", "Brust", "Körpergewicht",
       {"delta_vorne": 1.0, "brust_oben": 0.8, "serratus": 0.7,
        "trizeps_lateral": 0.5, "bauch_oben": 0.5},
       "druecken_horizontal", grunduebung=True,
       kg_anteil=0.85, reihe="planche", stufe=2,
       wdh_min=4, wdh_max=10, pause_s=120,
       ausfuehrung="Hände auf Hüfthöhe, Schultern weit vor die Hände schieben. "
                   "Die Vorbereitung auf die Planche.",
       fehler="Schultern bleiben über den Händen. Dann ist es eine normale Liegestütze."),
    _u("Tuck Planche", "Brust", "Körpergewicht",
       {"delta_vorne": 1.0, "serratus": 0.9, "brust_oben": 0.7,
        "bauch_unten": 0.7, "transversus": 0.7, "trizeps_lang": 0.5},
       "halten", kg_anteil=1.0, reihe="planche", stufe=3, ist_zeit=True,
       wdh_min=5, wdh_max=30, pause_s=150,
       ausfuehrung="Arme gestreckt, Knie angezogen, Füße frei. Schultern weit "
                   "vor den Händen, Rücken rund.",
       fehler="Ellenbogen gebeugt. Dann ist es kein Planche-Halt mehr."),

    # --- Kurzhantel ---
    _u("Kurzhantel-Bankdrücken", "Brust", "Kurzhantel",
       {"brust_mitte": 1.0, "brust_unten": 0.6, "trizeps_lateral": 0.6,
        "trizeps_medial": 0.5, "delta_vorne": 0.5},
       "druecken_horizontal", benoetigt=("kurzhantel", "bank"), grunduebung=True,
       wdh_min=6, wdh_max=15, pause_s=120,
       ausfuehrung="Hanteln auf Brusthöhe, Schulterblätter zusammen und nach unten, "
                   "nach oben zusammenführen ohne die Ellenbogen zu überstrecken.",
       fehler="Schulterblätter locker. Sie gehören während des ganzen Satzes fixiert."),
    _u("Kurzhantel-Bankdrücken am Boden", "Brust", "Kurzhantel",
       {"brust_mitte": 1.0, "trizeps_lateral": 0.7, "trizeps_medial": 0.6,
        "delta_vorne": 0.4},
       "druecken_horizontal", benoetigt=("kurzhantel",), grunduebung=True,
       wdh_min=6, wdh_max=15, pause_s=120,
       ausfuehrung="Auf dem Boden liegend. Die Ellenbogen stoppen am Boden, "
                   "der Weg ist kürzer und die Schulter wird geschont. "
                   "Die Heimvariante ohne Bank.",
       fehler="Schwung aus der Hüfte. Das Becken bleibt am Boden."),
    _u("Kurzhantel-Schrägbankdrücken", "Brust", "Kurzhantel",
       {"brust_oben": 1.0, "brust_mitte": 0.6, "delta_vorne": 0.7,
        "trizeps_lateral": 0.5},
       "druecken_schraeg", benoetigt=("kurzhantel", "schraegbank"), grunduebung=True,
       wdh_min=8, wdh_max=15, pause_s=120,
       ausfuehrung="Bank auf 30 bis 45 Grad. Steiler holt die Schulter die Arbeit.",
       fehler="Bank zu steil eingestellt. Über 45 Grad wird es Schulterdrücken."),
    _u("Kurzhantel-Fliegende", "Brust", "Kurzhantel",
       {"brust_mitte": 1.0, "brust_unten": 0.5, "delta_vorne": 0.3},
       "fliegende", benoetigt=("kurzhantel",),
       wdh_min=10, wdh_max=20, pause_s=75,
       ausfuehrung="Leicht gebeugte Ellenbogen, im Bogen öffnen und schließen. "
                   "Die Dehnung unten ist der Reiz, nicht das Gewicht.",
       fehler="Ellenbogen durchstrecken oder zu tief gehen. Beides belastet die Schulter."),
    _u("Kurzhantel-Überzüge", "Brust", "Kurzhantel",
       {"brust_mitte": 0.8, "latissimus": 0.8, "teres_major": 0.6,
        "trizeps_lang": 0.5, "serratus": 0.4},
       "fliegende", benoetigt=("kurzhantel",),
       wdh_min=10, wdh_max=15, pause_s=90,
       ausfuehrung="Quer auf einer Bank oder auf dem Boden, Hantel hinter dem Kopf "
                   "im Bogen führen. Trifft Brust und Latissimus zugleich."),
    _u("Enges Kurzhanteldrücken", "Brust", "Kurzhantel",
       {"trizeps_lateral": 1.0, "trizeps_medial": 0.9, "trizeps_lang": 0.7,
        "brust_mitte": 0.6, "delta_vorne": 0.4},
       "druecken_horizontal", benoetigt=("kurzhantel",),
       griff="neutral", wdh_min=8, wdh_max=15, pause_s=90,
       ausfuehrung="Hanteln aneinander, Ellenbogen eng am Körper. Der Trizeps trägt."),

    # --- Studio ---
    _u("Bankdrücken", "Brust", "Langhantel",
       {"brust_mitte": 1.0, "brust_unten": 0.6, "trizeps_lateral": 0.6,
        "trizeps_medial": 0.5, "delta_vorne": 0.6},
       "druecken_horizontal", benoetigt=("langhantel", "bank", "rack"),
       grunduebung=True, griff="obergriff",
       wdh_min=3, wdh_max=10, pause_s=180,
       ausfuehrung="Schulterblätter zusammen, Füße fest, Stange zum Brustbein.",
       fehler="Stange zu hoch angesetzt. Sie gehört auf Höhe der Brustwarzen."),
    _u("Schrägbankdrücken", "Brust", "Langhantel",
       {"brust_oben": 1.0, "delta_vorne": 0.7, "trizeps_lateral": 0.5,
        "brust_mitte": 0.5},
       "druecken_schraeg", benoetigt=("langhantel", "schraegbank", "rack"),
       grunduebung=True, griff="obergriff", wdh_min=6, wdh_max=12, pause_s=150),
    _u("Kabelzug-Crossover", "Brust", "Kabelzug",
       {"brust_mitte": 1.0, "brust_unten": 0.7, "delta_vorne": 0.3},
       "fliegende", benoetigt=("kabelzug",), wdh_min=12, wdh_max=20, pause_s=60,
       ausfuehrung="Zug von oben, Hände vor dem Bauch zusammenführen. "
                   "Von unten trifft es die obere Brust."),
    _u("Butterfly", "Brust", "Maschine",
       {"brust_mitte": 1.0, "brust_unten": 0.4, "delta_vorne": 0.2},
       "fliegende", benoetigt=("butterfly",), wdh_min=12, wdh_max=20, pause_s=60),
    _u("Band-Fliegende", "Brust", "Band",
       {"brust_mitte": 1.0, "brust_unten": 0.5, "delta_vorne": 0.3},
       "fliegende", benoetigt=("band",), wdh_min=12, wdh_max=25, pause_s=60,
       ausfuehrung="Band hinter dem Rücken oder am Türanker, Hände vor der Brust "
                   "zusammenführen. Der Widerstand ist oben am größten, genau dort, "
                   "wo die Kurzhantel keinen mehr hat."),
    _u("Dips", "Brust", "Körpergewicht",
       {"brust_unten": 1.0, "trizeps_lateral": 0.9, "trizeps_lang": 0.8,
        "trizeps_medial": 0.7, "delta_vorne": 0.6, "brust_mitte": 0.5},
       "dip", benoetigt=("dip_barren",), grunduebung=True,
       kg_anteil=1.0, reihe="dip", stufe=3, wdh_min=5, wdh_max=15, pause_s=120,
       ausfuehrung="Oberkörper leicht nach vorne geneigt trifft die Brust, "
                   "aufrecht den Trizeps. Bis die Oberarme waagerecht sind.",
       fehler="Zu tief. Wer unter 90 Grad geht, holt sich Schulterprobleme."),
    _u("Bank-Dips", "Brust", "Körpergewicht",
       {"trizeps_lateral": 1.0, "trizeps_medial": 0.8, "trizeps_lang": 0.7,
        "brust_unten": 0.5, "delta_vorne": 0.5},
       "dip", benoetigt=("stuhl",), kg_anteil=0.55, reihe="dip", stufe=1,
       wdh_min=8, wdh_max=20, pause_s=75,
       ausfuehrung="Hände auf der Stuhlkante hinter dem Rücken, Füße vor sich. "
                   "Weiter weg heißt schwerer.",
       fehler="Schultern hochgezogen. Sie bleiben unten, sonst klemmt es vorne."),
    _u("Negative Dips", "Brust", "Körpergewicht",
       {"brust_unten": 1.0, "trizeps_lateral": 0.9, "trizeps_lang": 0.7,
        "delta_vorne": 0.6},
       "dip", benoetigt=("dip_barren",), kg_anteil=1.0, reihe="dip", stufe=2,
       wdh_min=3, wdh_max=8, pause_s=120,
       ausfuehrung="Oben mit gestreckten Armen starten, drei bis fünf Sekunden "
                   "absenken, mit den Füßen wieder hochsteigen. Der Weg zum "
                   "ersten sauberen Dip.",
       fehler="Fallen lassen. Es zählt nur, was gebremst wird."),
    _u("Dips mit Zusatzgewicht", "Brust", "Körpergewicht",
       {"brust_unten": 1.0, "trizeps_lateral": 0.9, "trizeps_lang": 0.8,
        "trizeps_medial": 0.7, "delta_vorne": 0.6, "brust_mitte": 0.5},
       "dip", benoetigt=("dip_barren", "rucksack"), grunduebung=True,
       kg_anteil=1.0, reihe="dip", stufe=4, wdh_min=4, wdh_max=10, pause_s=150,
       ausfuehrung="Sobald fünfzehn saubere Dips gehen, ist Zusatzgewicht der "
                   "nächste Schritt und nicht mehr Wiederholungen."),
]


# ===========================================================================
# RUECKEN
# ===========================================================================

_RUECKEN = [
    # --- Klimmzug-Reihe, mit Griffen als eigene Uebungen ---
    _u("Negative Klimmzüge", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "teres_major": 0.6, "bizeps_lang": 0.6,
        "bizeps_kurz": 0.5, "brachialis": 0.5, "rhomboiden": 0.5,
        "trapez_unten": 0.4, "unterarm_beuger": 0.5},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=1.0, griff="obergriff", reihe="klimmzug", stufe=2,
       wdh_min=3, wdh_max=8, pause_s=120,
       ausfuehrung="Oben starten, so langsam wie möglich absenken, drei bis fünf "
                   "Sekunden. Der Weg zum ersten echten Klimmzug.",
       fehler="Zu schnell fallen lassen. Die langsame Phase ist die ganze Übung."),
    _u("Klimmzüge Obergriff", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "teres_major": 0.7, "rhomboiden": 0.6,
        "trapez_unten": 0.6, "bizeps_lang": 0.6, "brachialis": 0.5,
        "unterarm_beuger": 0.5, "delta_hinten": 0.3, "bauch_oben": 0.3},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=1.0, griff="obergriff", reihe="klimmzug", stufe=3,
       wdh_min=4, wdh_max=12, pause_s=150,
       ausfuehrung="Handrücken zeigt zu dir, Griff etwas weiter als schulterbreit. "
                   "Brust zur Stange, Schulterblätter zuerst nach unten ziehen.",
       fehler="Nur die Arme ziehen. Der Zug beginnt im Schulterblatt, nicht im Ellenbogen."),
    _u("Klimmzüge Untergriff", "Rücken", "Körpergewicht",
       {"bizeps_lang": 1.0, "bizeps_kurz": 0.9, "latissimus": 0.9,
        "brachialis": 0.7, "teres_major": 0.5, "unterarm_beuger": 0.5,
        "rhomboiden": 0.4, "bauch_oben": 0.3},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=1.0, griff="untergriff", reihe="klimmzug", stufe=3,
       wdh_min=5, wdh_max=12, pause_s=150,
       ausfuehrung="Handflächen zeigen zu dir, etwa schulterbreit. Der Bizeps kann "
                   "voll mitarbeiten, deshalb schafft man hier meist mehr als im Obergriff.",
       fehler="Ellenbogen nach außen. Sie bleiben eng am Körper."),
    _u("Klimmzüge neutraler Griff", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "brachialis": 0.8, "bizeps_lang": 0.7,
        "teres_major": 0.6, "brachioradialis": 0.6, "rhomboiden": 0.5,
        "trapez_unten": 0.5},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=1.0, griff="neutral", reihe="klimmzug", stufe=3,
       wdh_min=5, wdh_max=12, pause_s=150,
       ausfuehrung="Handflächen zeigen zueinander. Die schulterfreundlichste Variante "
                   "und die, bei der der Brachialis am meisten arbeitet."),
    _u("Breite Klimmzüge", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "teres_major": 0.8, "rhomboiden": 0.6,
        "trapez_mitte": 0.5, "delta_hinten": 0.4, "bizeps_lang": 0.4},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=1.0, griff="obergriff", reihe="klimmzug", stufe=4,
       wdh_min=4, wdh_max=10, pause_s=150,
       ausfuehrung="Deutlich weiter als schulterbreit. Kürzerer Weg, mehr Breite "
                   "im Latissimus, weniger Bizeps.",
       fehler="So weit greifen, dass der Weg fast null wird. Breiter ist nicht besser."),
    _u("Klimmzüge mit Zusatzgewicht", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "teres_major": 0.7, "rhomboiden": 0.6,
        "trapez_unten": 0.6, "bizeps_lang": 0.6, "unterarm_beuger": 0.5},
       "ziehen_vertikal", benoetigt=("klimmzugstange", "rucksack"), grunduebung=True,
       kg_anteil=1.0, griff="obergriff", reihe="klimmzug", stufe=5,
       wdh_min=3, wdh_max=8, pause_s=180,
       ausfuehrung="Rucksack, Dipgürtel oder Weste. Sobald zwölf saubere Klimmzüge "
                   "gehen, ist Zusatzgewicht der nächste Schritt und nicht mehr Wiederholungen."),
    _u("Archer-Klimmzüge", "Rücken", "Körpergewicht",
       {"latissimus": 1.0, "teres_major": 0.8, "bizeps_lang": 0.7,
        "obliquus_extern": 0.5, "rhomboiden": 0.5},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), grunduebung=True,
       einseitig=True, kg_anteil=1.0, griff="obergriff",
       reihe="klimmzug", stufe=6, wdh_min=2, wdh_max=6, pause_s=180,
       ausfuehrung="Breiter Griff, zu einer Hand hochziehen, der andere Arm bleibt "
                   "gestreckt. Vorstufe zum einarmigen Klimmzug."),
    _u("Kinnstange-Hang", "Rücken", "Körpergewicht",
       {"unterarm_beuger": 1.0, "latissimus": 0.5, "trapez_unten": 0.4,
        "bauch_oben": 0.3},
       "halten", benoetigt=("klimmzugstange",), kg_anteil=1.0,
       reihe="klimmzug", stufe=1, ist_zeit=True,
       wdh_min=20, wdh_max=60, pause_s=90,
       ausfuehrung="Einfach hängen, Schultern aktiv nach unten. Baut Griffkraft "
                   "und gewöhnt die Schulter an die Zugbelastung."),

    # --- Rudern ohne Studio ---
    _u("Australian Rows", "Rücken", "Körpergewicht",
       {"rhomboiden": 1.0, "trapez_mitte": 0.9, "latissimus": 0.8,
        "delta_hinten": 0.7, "bizeps_lang": 0.6, "trapez_unten": 0.5,
        "erector_spinae": 0.3},
       "ziehen_horizontal", benoetigt=("klimmzugstange",), grunduebung=True,
       kg_anteil=0.55, griff="obergriff", reihe="rudern", stufe=2,
       wdh_min=8, wdh_max=20, pause_s=90,
       ausfuehrung="Unter einer tiefen Stange oder einem Tisch, Körper gestreckt, "
                   "Brust zur Stange ziehen. Je waagerechter, desto schwerer.",
       fehler="Hüfte hängt durch. Der Körper bleibt ein Brett."),
    _u("Tisch-Rudern", "Rücken", "Körpergewicht",
       {"rhomboiden": 1.0, "trapez_mitte": 0.8, "latissimus": 0.7,
        "bizeps_lang": 0.6, "delta_hinten": 0.6},
       "ziehen_horizontal", benoetigt=("stuhl",), kg_anteil=0.50,
       reihe="rudern", stufe=1, wdh_min=8, wdh_max=20, pause_s=75,
       ausfuehrung="Unter einen stabilen Tisch legen, an der Kante hochziehen. "
                   "Das Rudern für Wohnungen ohne Stange."),
    _u("Kurzhantelrudern einarmig", "Rücken", "Kurzhantel",
       {"latissimus": 1.0, "rhomboiden": 0.7, "trapez_mitte": 0.6,
        "teres_major": 0.6, "bizeps_lang": 0.5, "delta_hinten": 0.5,
        "erector_spinae": 0.4, "obliquus_extern": 0.3},
       "ziehen_horizontal", benoetigt=("kurzhantel",), grunduebung=True,
       einseitig=True, griff="neutral", wdh_min=8, wdh_max=15, pause_s=90,
       ausfuehrung="Eine Hand und ein Knie auf der Bank oder dem Stuhl, Rücken "
                   "waagerecht, Hantel zur Hüfte ziehen.",
       fehler="Oberkörper dreht mit. Die Schulter geht hoch, der Rumpf bleibt ruhig."),
    _u("Kurzhantelrudern beidarmig", "Rücken", "Kurzhantel",
       {"latissimus": 1.0, "rhomboiden": 0.8, "trapez_mitte": 0.7,
        "delta_hinten": 0.6, "bizeps_lang": 0.5, "erector_spinae": 0.6},
       "ziehen_horizontal", benoetigt=("kurzhantel",), grunduebung=True,
       griff="neutral", wdh_min=8, wdh_max=15, pause_s=120,
       ausfuehrung="Vorgebeugt mit geradem Rücken, beide Hanteln zur Hüfte."),
    _u("Kurzhantel-Reverse-Flys", "Rücken", "Kurzhantel",
       {"delta_hinten": 1.0, "rhomboiden": 0.8, "trapez_mitte": 0.7,
        "rotatorenmanschette": 0.4},
       "reverse_fly", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=20, pause_s=60,
       ausfuehrung="Vorgebeugt, leicht gebeugte Ellenbogen, im Bogen zur Seite öffnen. "
                   "Leichter als man denkt: der Muskel ist klein.",
       fehler="Zu schwer gewählt, dann übernimmt der Trapez."),
    _u("Kurzhantel-Überzüge liegend", "Rücken", "Kurzhantel",
       {"latissimus": 1.0, "teres_major": 0.7, "brust_mitte": 0.6,
        "trizeps_lang": 0.5},
       "fliegende", benoetigt=("kurzhantel",), wdh_min=10, wdh_max=15, pause_s=75),
    _u("Band-Latzug", "Rücken", "Band",
       {"latissimus": 1.0, "teres_major": 0.6, "bizeps_lang": 0.5,
        "trapez_unten": 0.5, "rhomboiden": 0.4},
       "ziehen_vertikal", benoetigt=("band",), wdh_min=12, wdh_max=20, pause_s=60,
       ausfuehrung="Band oben befestigen, im Knien zur Brust ziehen. "
                   "Der Latzug für zu Hause."),
    _u("Band-Rudern", "Rücken", "Band",
       {"rhomboiden": 1.0, "trapez_mitte": 0.8, "latissimus": 0.7,
        "delta_hinten": 0.6, "bizeps_lang": 0.5},
       "ziehen_horizontal", benoetigt=("band",), wdh_min=12, wdh_max=20, pause_s=60),
    _u("Band-Pull-Aparts", "Rücken", "Band",
       {"delta_hinten": 1.0, "rhomboiden": 0.8, "trapez_mitte": 0.8,
        "rotatorenmanschette": 0.5},
       "reverse_fly", benoetigt=("band",), wdh_min=15, wdh_max=30, pause_s=45,
       ausfuehrung="Band vor der Brust auf Armlänge auseinanderziehen. "
                   "Die beste Gegenübung zu allem, was man drückt."),

    # --- Studio ---
    _u("Latzug", "Rücken", "Kabelzug",
       {"latissimus": 1.0, "teres_major": 0.7, "bizeps_lang": 0.6,
        "rhomboiden": 0.5, "trapez_unten": 0.5},
       "ziehen_vertikal", benoetigt=("latzug",), grunduebung=True,
       griff="obergriff", wdh_min=8, wdh_max=15, pause_s=90),
    _u("Latzug Untergriff", "Rücken", "Kabelzug",
       {"latissimus": 1.0, "bizeps_lang": 0.8, "bizeps_kurz": 0.7,
        "teres_major": 0.5},
       "ziehen_vertikal", benoetigt=("latzug",), griff="untergriff",
       wdh_min=8, wdh_max=15, pause_s=90),
    _u("Kabelrudern sitzend", "Rücken", "Kabelzug",
       {"rhomboiden": 1.0, "trapez_mitte": 0.9, "latissimus": 0.8,
        "delta_hinten": 0.6, "bizeps_lang": 0.5},
       "ziehen_horizontal", benoetigt=("rudermaschine_kabel",), grunduebung=True,
       wdh_min=8, wdh_max=15, pause_s=90),
    _u("Langhantelrudern", "Rücken", "Langhantel",
       {"latissimus": 1.0, "rhomboiden": 0.8, "trapez_mitte": 0.7,
        "delta_hinten": 0.6, "bizeps_lang": 0.5, "erector_spinae": 0.7},
       "ziehen_horizontal", benoetigt=("langhantel",), grunduebung=True,
       griff="obergriff", wdh_min=5, wdh_max=12, pause_s=150),
    _u("Kreuzheben", "Rücken", "Langhantel",
       {"erector_spinae": 1.0, "gluteus_maximus": 1.0, "biceps_femoris": 0.9,
        "semitendinosus": 0.8, "trapez_oben": 0.6, "latissimus": 0.5,
        "unterarm_beuger": 0.6, "quadratus_lumborum": 0.5,
        "vastus_lateralis": 0.4, "transversus": 0.5},
       "hueftstreckung", benoetigt=("langhantel",), grunduebung=True,
       griff="gemischt", wdh_min=3, wdh_max=8, pause_s=210,
       ausfuehrung="Stange über der Mitte des Fußes, Rücken gerade, mit den Beinen "
                   "drücken statt mit dem Rücken ziehen.",
       fehler="Runder Rücken. Ein einziger Satz reicht, um Wochen zu verlieren."),
    _u("Face Pulls", "Rücken", "Kabelzug",
       {"delta_hinten": 1.0, "rotatorenmanschette": 0.8, "trapez_mitte": 0.7,
        "rhomboiden": 0.6, "trapez_oben": 0.4},
       "reverse_fly", benoetigt=("kabelzug",), wdh_min=15, wdh_max=25, pause_s=60,
       ausfuehrung="Seil auf Gesichtshöhe, zu den Ohren ziehen, außenrotieren. "
                   "Die Versicherung für jede Schulter, die viel drückt."),
    _u("Hyperextensions", "Rücken", "Körpergewicht",
       {"erector_spinae": 1.0, "gluteus_maximus": 0.7, "biceps_femoris": 0.6,
        "quadratus_lumborum": 0.5},
       "hueftstreckung", benoetigt=("hyperextension",), kg_anteil=0.45,
       wdh_min=10, wdh_max=20, pause_s=75),
    _u("Superman", "Rücken", "Körpergewicht",
       {"erector_spinae": 1.0, "gluteus_maximus": 0.6, "trapez_unten": 0.4,
        "delta_hinten": 0.3},
       "hueftstreckung", kg_anteil=0.15, wdh_min=10, wdh_max=20, pause_s=45,
       ausfuehrung="Bauchlage, Arme und Beine gleichzeitig anheben, kurz halten. "
                   "Der Rückenstrecker ohne jedes Gerät."),
    _u("Kurzhantel-Shrugs", "Rücken", "Kurzhantel",
       {"trapez_oben": 1.0, "trapez_mitte": 0.4, "unterarm_beuger": 0.5,
        "nacken": 0.3},
       "seitheben", benoetigt=("kurzhantel",), wdh_min=10, wdh_max=20, pause_s=75,
       ausfuehrung="Schultern gerade nach oben, kurz halten. Nicht kreisen.",
       fehler="Kreisende Schultern. Das bringt nichts und reizt das Gelenk."),
]


# ===========================================================================
# SCHULTERN
# ===========================================================================

_SCHULTERN = [
    _u("Kurzhantel-Schulterdrücken", "Schultern", "Kurzhantel",
       {"delta_vorne": 1.0, "delta_seite": 0.7, "trizeps_lateral": 0.6,
        "trizeps_medial": 0.5, "trapez_oben": 0.4, "serratus": 0.3},
       "druecken_vertikal", benoetigt=("kurzhantel",), grunduebung=True,
       wdh_min=6, wdh_max=15, pause_s=120,
       ausfuehrung="Sitzend oder stehend, Hanteln von Ohrhöhe nach oben. "
                   "Stehend arbeitet der Rumpf mit.",
       fehler="Ins Hohlkreuz ausweichen. Bauch anspannen, Rippen unten lassen."),
    _u("Arnold-Drücken", "Schultern", "Kurzhantel",
       {"delta_vorne": 1.0, "delta_seite": 0.8, "trizeps_lateral": 0.5,
        "trapez_oben": 0.4},
       "druecken_vertikal", benoetigt=("kurzhantel",),
       wdh_min=8, wdh_max=15, pause_s=90,
       ausfuehrung="Unten Handflächen zum Körper, beim Drücken nach außen drehen. "
                   "Holt die seitliche Schulter stärker mit."),
    _u("Seitheben", "Schultern", "Kurzhantel",
       {"delta_seite": 1.0, "trapez_oben": 0.3, "delta_vorne": 0.2},
       "seitheben", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=25, pause_s=60,
       ausfuehrung="Leicht gebeugte Ellenbogen, bis Schulterhöhe, kleiner Finger "
                   "leicht höher. Langsam ablassen.",
       fehler="Mit Schwung hochreißen. Der Muskel ist klein, das Gewicht muss es auch sein."),
    _u("Seitheben am Band", "Schultern", "Band",
       {"delta_seite": 1.0, "trapez_oben": 0.3},
       "seitheben", benoetigt=("band",), wdh_min=15, wdh_max=30, pause_s=45,
       ausfuehrung="Auf das Band stellen, zur Seite heben. Der Widerstand wächst "
                   "nach oben, wo der Muskel am stärksten ist."),
    _u("Frontheben", "Schultern", "Kurzhantel",
       {"delta_vorne": 1.0, "brust_oben": 0.3, "delta_seite": 0.2},
       "frontheben", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=20, pause_s=60,
       ausfuehrung="Bis Schulterhöhe, nicht höher. Nur nötig, wenn kaum gedrückt wird."),
    _u("Aufrechtes Rudern", "Schultern", "Kurzhantel",
       {"delta_seite": 1.0, "trapez_oben": 0.8, "bizeps_lang": 0.3,
        "delta_vorne": 0.4},
       "seitheben", benoetigt=("kurzhantel",), wdh_min=10, wdh_max=15, pause_s=75,
       ausfuehrung="Ellenbogen führen, nur bis Brusthöhe.",
       fehler="Zu hoch ziehen. Über Brusthöhe klemmt die Schulter ein."),
    _u("Pike-Liegestütze", "Schultern", "Körpergewicht",
       {"delta_vorne": 1.0, "delta_seite": 0.6, "trizeps_lateral": 0.7,
        "trizeps_medial": 0.6, "serratus": 0.5, "trapez_oben": 0.4},
       "druecken_vertikal", grunduebung=True, kg_anteil=0.60,
       reihe="handstand", stufe=2, wdh_min=6, wdh_max=15, pause_s=90,
       ausfuehrung="Aus dem umgedrehten V heraus den Kopf zum Boden senken. "
                   "Das Schulterdrücken ohne Hanteln.",
       fehler="Hüfte sinkt ab. Je steiler der Rücken, desto mehr Schulter."),
    _u("Pike-Liegestütze erhöht", "Schultern", "Körpergewicht",
       {"delta_vorne": 1.0, "delta_seite": 0.7, "trizeps_lateral": 0.7,
        "serratus": 0.6, "trapez_oben": 0.5},
       "druecken_vertikal", benoetigt=("stuhl",), grunduebung=True,
       kg_anteil=0.72, reihe="handstand", stufe=3, wdh_min=5, wdh_max=12, pause_s=120,
       ausfuehrung="Füße erhöht, damit der Oberkörper fast senkrecht steht."),
    _u("Handstand-Liegestütze an der Wand", "Schultern", "Körpergewicht",
       {"delta_vorne": 1.0, "delta_seite": 0.8, "trizeps_lateral": 0.9,
        "trizeps_medial": 0.8, "serratus": 0.7, "trapez_oben": 0.6,
        "bauch_oben": 0.4},
       "druecken_vertikal", benoetigt=("wand",), grunduebung=True,
       kg_anteil=0.95, reihe="handstand", stufe=4, wdh_min=2, wdh_max=8, pause_s=180,
       ausfuehrung="Mit den Füßen an der Wand, kontrolliert absenken bis der Kopf "
                   "den Boden fast berührt.",
       fehler="Absenken ohne Kontrolle. Erst den Handstand halten können, dann drücken."),
    _u("Handstand halten", "Schultern", "Körpergewicht",
       {"delta_vorne": 1.0, "delta_seite": 0.6, "trapez_oben": 0.6,
        "serratus": 0.6, "bauch_oben": 0.5, "unterarm_beuger": 0.5},
       "halten", benoetigt=("wand",), kg_anteil=0.9, reihe="handstand", stufe=1,
       ist_zeit=True, wdh_min=15, wdh_max=60, pause_s=120),
    _u("Schulterdrücken", "Schultern", "Langhantel",
       {"delta_vorne": 1.0, "delta_seite": 0.7, "trizeps_lateral": 0.6,
        "trapez_oben": 0.5, "bauch_oben": 0.4},
       "druecken_vertikal", benoetigt=("langhantel",), grunduebung=True,
       griff="obergriff", wdh_min=4, wdh_max=10, pause_s=150),
    _u("Reverse Flys", "Schultern", "Kurzhantel",
       {"delta_hinten": 1.0, "rhomboiden": 0.7, "trapez_mitte": 0.6},
       "reverse_fly", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=20, pause_s=60),
    _u("Kubanische Rotation", "Schultern", "Kurzhantel",
       {"rotatorenmanschette": 1.0, "delta_hinten": 0.6, "trapez_mitte": 0.4},
       "rotation", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=20, pause_s=45,
       ausfuehrung="Sehr leicht. Vorbeugend für alle, die viel über Kopf drücken."),
]


# ===========================================================================
# ARME
# ===========================================================================

_ARME = [
    _u("Bizeps-Curls Kurzhantel", "Arme", "Kurzhantel",
       {"bizeps_lang": 1.0, "bizeps_kurz": 0.9, "brachialis": 0.6,
        "unterarm_beuger": 0.4},
       "armbeugen", benoetigt=("kurzhantel",), griff="untergriff",
       wdh_min=8, wdh_max=15, pause_s=75,
       ausfuehrung="Ellenbogen am Körper, nur der Unterarm bewegt sich.",
       fehler="Schwung aus dem Rücken. Dann trainiert man den Rücken, nicht den Bizeps."),
    _u("Hammer-Curls", "Arme", "Kurzhantel",
       {"brachialis": 1.0, "brachioradialis": 0.9, "bizeps_lang": 0.7,
        "unterarm_beuger": 0.5},
       "armbeugen", benoetigt=("kurzhantel",), griff="neutral",
       wdh_min=8, wdh_max=15, pause_s=75,
       ausfuehrung="Handflächen zeigen zueinander. Trifft den Brachialis, "
                   "der den Bizeps von unten anhebt."),
    _u("Konzentrationscurls", "Arme", "Kurzhantel",
       {"bizeps_kurz": 1.0, "bizeps_lang": 0.7, "brachialis": 0.5},
       "armbeugen", benoetigt=("kurzhantel",), einseitig=True, griff="untergriff",
       wdh_min=10, wdh_max=15, pause_s=60,
       ausfuehrung="Sitzend, Ellenbogen am Innenschenkel abgestützt. "
                   "Keine Chance zu schummeln."),
    _u("Schrägbank-Curls", "Arme", "Kurzhantel",
       {"bizeps_lang": 1.0, "bizeps_kurz": 0.6, "brachialis": 0.5},
       "armbeugen", benoetigt=("kurzhantel", "schraegbank"), griff="untergriff",
       wdh_min=10, wdh_max=15, pause_s=75,
       ausfuehrung="Zurückgelehnt hängen die Arme hinter dem Körper. Der lange Kopf "
                   "startet gedehnt und arbeitet dadurch mehr."),
    _u("Band-Curls", "Arme", "Band",
       {"bizeps_lang": 1.0, "bizeps_kurz": 0.8, "brachialis": 0.5},
       "armbeugen", benoetigt=("band",), griff="untergriff",
       wdh_min=12, wdh_max=25, pause_s=60),
    _u("Bizeps-Curls Langhantel", "Arme", "Langhantel",
       {"bizeps_lang": 1.0, "bizeps_kurz": 1.0, "brachialis": 0.6,
        "unterarm_beuger": 0.4},
       "armbeugen", benoetigt=("langhantel",), griff="untergriff",
       wdh_min=8, wdh_max=12, pause_s=90),
    _u("Chin-Up-Halten", "Arme", "Körpergewicht",
       {"bizeps_lang": 1.0, "bizeps_kurz": 0.9, "latissimus": 0.6,
        "unterarm_beuger": 0.6},
       "halten", benoetigt=("klimmzugstange",), kg_anteil=1.0, ist_zeit=True,
       griff="untergriff", wdh_min=10, wdh_max=45, pause_s=90,
       ausfuehrung="Oben in der Klimmzugposition halten, Kinn über der Stange. "
                   "Der Bizeps-Reiz ohne jede Hantel."),

    _u("Trizeps-Kickbacks", "Arme", "Kurzhantel",
       {"trizeps_lateral": 1.0, "trizeps_lang": 0.7, "trizeps_medial": 0.6},
       "armstrecken", benoetigt=("kurzhantel",), einseitig=True,
       wdh_min=12, wdh_max=20, pause_s=60),
    _u("Überkopf-Trizepsdrücken", "Arme", "Kurzhantel",
       {"trizeps_lang": 1.0, "trizeps_medial": 0.7, "trizeps_lateral": 0.6},
       "armstrecken", benoetigt=("kurzhantel",), wdh_min=10, wdh_max=15, pause_s=75,
       ausfuehrung="Hantel hinter dem Kopf, Ellenbogen zeigen nach oben. "
                   "Die einzige Trizeps-Übung, die den langen Kopf voll dehnt."),
    _u("Französisches Drücken", "Arme", "Kurzhantel",
       {"trizeps_lang": 1.0, "trizeps_lateral": 0.8, "trizeps_medial": 0.7},
       "armstrecken", benoetigt=("kurzhantel",), wdh_min=10, wdh_max=15, pause_s=90,
       ausfuehrung="Liegend, Hanteln zur Stirn absenken. Ellenbogen bleiben stehen.",
       fehler="Ellenbogen wandern zurück. Dann wird daraus ein Überzug."),
    _u("Trizepsdrücken am Kabel", "Arme", "Kabelzug",
       {"trizeps_lateral": 1.0, "trizeps_medial": 0.8, "trizeps_lang": 0.5},
       "armstrecken", benoetigt=("kabelzug",), wdh_min=10, wdh_max=20, pause_s=60),
    _u("Band-Trizepsdrücken", "Arme", "Band",
       {"trizeps_lateral": 1.0, "trizeps_medial": 0.8, "trizeps_lang": 0.5},
       "armstrecken", benoetigt=("band",), wdh_min=15, wdh_max=25, pause_s=45),
    _u("Handgelenks-Curls", "Arme", "Kurzhantel",
       {"unterarm_beuger": 1.0},
       "armbeugen", benoetigt=("kurzhantel",), wdh_min=15, wdh_max=25, pause_s=45),
    _u("Umgekehrte Handgelenks-Curls", "Arme", "Kurzhantel",
       {"unterarm_strecker": 1.0},
       "armbeugen", benoetigt=("kurzhantel",), wdh_min=15, wdh_max=25, pause_s=45),
    _u("Farmers Walk", "Arme", "Kurzhantel",
       {"unterarm_beuger": 1.0, "trapez_oben": 0.7, "transversus": 0.5,
        "obliquus_extern": 0.4, "erector_spinae": 0.4},
       "halten", benoetigt=("kurzhantel",), ist_zeit=True,
       wdh_min=30, wdh_max=90, pause_s=90,
       ausfuehrung="Schwer tragen, aufrecht gehen. Griffkraft, Rumpf und Trapez "
                   "in einer Übung."),
]


# ===========================================================================
# BEINE
# ===========================================================================

_BEINE = [
    # --- Koerpergewicht ---
    _u("Kniebeugen Körpergewicht", "Beine", "Körpergewicht",
       {"rectus_femoris": 1.0, "vastus_lateralis": 1.0, "vastus_medialis": 1.0,
        "vastus_intermedius": 0.9, "gluteus_maximus": 0.8, "adduktoren": 0.5,
        "erector_spinae": 0.3, "transversus": 0.3},
       "beugen_knie", grunduebung=True, kg_anteil=0.70,
       reihe="kniebeuge", stufe=1, wdh_min=12, wdh_max=30, pause_s=60,
       ausfuehrung="Füße schulterbreit, Knie folgen den Zehen, so tief wie die "
                   "Beweglichkeit erlaubt.",
       fehler="Fersen heben ab. Dann fehlt Sprunggelenks-Beweglichkeit, "
              "erhöhte Fersen helfen übergangsweise."),
    _u("Sumo-Kniebeugen", "Beine", "Körpergewicht",
       {"adduktoren": 1.0, "gluteus_maximus": 0.9, "vastus_medialis": 0.8,
        "rectus_femoris": 0.6, "gluteus_medius": 0.5},
       "beugen_knie", grunduebung=True, kg_anteil=0.70,
       wdh_min=12, wdh_max=25, pause_s=75,
       ausfuehrung="Sehr breiter Stand, Zehen nach außen. Holt die Adduktoren "
                   "und das Gesäß stärker als die enge Version."),
    _u("Bulgarische Kniebeugen", "Beine", "Körpergewicht",
       {"rectus_femoris": 1.0, "vastus_lateralis": 0.9, "vastus_medialis": 0.9,
        "gluteus_maximus": 0.9, "gluteus_medius": 0.6, "adduktoren": 0.5,
        "biceps_femoris": 0.4},
       "ausfallschritt", benoetigt=("stuhl",), grunduebung=True, einseitig=True,
       kg_anteil=0.80, reihe="kniebeuge", stufe=3, wdh_min=8, wdh_max=15, pause_s=90,
       ausfuehrung="Hinterer Fuß auf Stuhl oder Bank, vorderes Bein trägt fast alles. "
                   "Die härteste Beinübung ohne Gewicht.",
       fehler="Vorderer Fuß zu nah. Er gehört so weit vor, dass das Knie über "
              "dem Sprunggelenk bleibt."),
    _u("Ausfallschritte", "Beine", "Körpergewicht",
       {"rectus_femoris": 1.0, "vastus_lateralis": 0.8, "gluteus_maximus": 0.8,
        "vastus_medialis": 0.8, "biceps_femoris": 0.4, "gluteus_medius": 0.5},
       "ausfallschritt", grunduebung=True, einseitig=True, kg_anteil=0.72,
       reihe="kniebeuge", stufe=2, wdh_min=10, wdh_max=20, pause_s=75),
    _u("Rückwärts-Ausfallschritte", "Beine", "Körpergewicht",
       {"gluteus_maximus": 1.0, "rectus_femoris": 0.8, "vastus_lateralis": 0.7,
        "biceps_femoris": 0.5, "gluteus_medius": 0.5},
       "ausfallschritt", grunduebung=True, einseitig=True, kg_anteil=0.72,
       wdh_min=10, wdh_max=20, pause_s=75,
       ausfuehrung="Nach hinten treten statt nach vorne. Schont das Knie und "
                   "trifft das Gesäß mehr."),
    _u("Pistol-Kniebeugen auf Erhöhung", "Beine", "Körpergewicht",
       {"vastus_lateralis": 1.0, "vastus_medialis": 1.0, "rectus_femoris": 0.9,
        "gluteus_maximus": 0.8, "gluteus_medius": 0.6, "transversus": 0.4},
       "beugen_knie", benoetigt=("stuhl",), grunduebung=True, einseitig=True,
       kg_anteil=0.80, reihe="kniebeuge", stufe=4, wdh_min=5, wdh_max=12,
       pause_s=105,
       ausfuehrung="Einbeinig auf einen Stuhl absetzen und wieder hoch. Je "
                   "niedriger die Sitzfläche, desto näher an der freien Pistol.",
       fehler="Sich auf die Fläche fallen lassen. Nur antippen, nicht absetzen."),
    _u("Pistol-Kniebeugen", "Beine", "Körpergewicht",
       {"vastus_lateralis": 1.0, "vastus_medialis": 1.0, "rectus_femoris": 1.0,
        "gluteus_maximus": 0.8, "gluteus_medius": 0.7, "transversus": 0.5,
        "biceps_femoris": 0.4},
       "beugen_knie", grunduebung=True, einseitig=True, kg_anteil=0.85,
       reihe="kniebeuge", stufe=5, wdh_min=3, wdh_max=10, pause_s=120,
       ausfuehrung="Einbeinig ganz nach unten, das andere Bein gestreckt nach vorne. "
                   "Braucht Kraft und Beweglichkeit zugleich.",
       fehler="Zu früh voll versuchen. Erst an einer Halterung oder auf eine Erhöhung."),
    _u("Sissy-Kniebeugen", "Beine", "Körpergewicht",
       {"rectus_femoris": 1.0, "vastus_lateralis": 0.8, "vastus_medialis": 0.8,
        "hueftbeuger": 0.4},
       "beugen_knie", kg_anteil=0.60, wdh_min=8, wdh_max=15, pause_s=75,
       ausfuehrung="Knie nach vorne, Oberkörper nach hinten, Hüfte bleibt gestreckt. "
                   "Isoliert den Quadrizeps stärker als jede normale Kniebeuge."),
    _u("Wandsitzen", "Beine", "Körpergewicht",
       {"vastus_lateralis": 1.0, "vastus_medialis": 1.0, "rectus_femoris": 0.8,
        "gluteus_maximus": 0.4},
       "halten", benoetigt=("wand",), kg_anteil=0.60, ist_zeit=True,
       wdh_min=30, wdh_max=120, pause_s=75),
    _u("Glute Bridge", "Beine", "Körpergewicht",
       {"gluteus_maximus": 1.0, "biceps_femoris": 0.6, "semitendinosus": 0.5,
        "erector_spinae": 0.3},
       "hueftstreckung", kg_anteil=0.35, wdh_min=12, wdh_max=25, pause_s=60,
       ausfuehrung="Rückenlage, Füße aufgestellt, Becken hochdrücken und oben "
                   "kurz halten."),
    _u("Einbeinige Glute Bridge", "Beine", "Körpergewicht",
       {"gluteus_maximus": 1.0, "biceps_femoris": 0.7, "gluteus_medius": 0.6,
        "semitendinosus": 0.5},
       "hueftstreckung", einseitig=True, kg_anteil=0.45,
       wdh_min=10, wdh_max=20, pause_s=60),
    _u("Nordic Curls", "Beine", "Körpergewicht",
       {"biceps_femoris": 1.0, "semitendinosus": 1.0, "gluteus_maximus": 0.5,
        "erector_spinae": 0.4},
       "hueftstreckung", grunduebung=True, kg_anteil=0.70,
       wdh_min=3, wdh_max=8, pause_s=120,
       ausfuehrung="Kniend, Füße fixiert, langsam nach vorne absinken lassen. "
                   "Die stärkste Beinbizeps-Übung ohne Gerät.",
       fehler="Sich fallen lassen. Es zählt nur, was gebremst wird."),
    _u("Hip Thrusts einbeinig", "Beine", "Körpergewicht",
       {"gluteus_maximus": 1.0, "biceps_femoris": 0.6, "gluteus_medius": 0.6},
       "hueftstreckung", benoetigt=("stuhl",), einseitig=True, kg_anteil=0.50,
       wdh_min=10, wdh_max=20, pause_s=75),
    _u("Wadenheben einbeinig", "Beine", "Körpergewicht",
       {"gastrocnemius": 1.0, "soleus": 0.7},
       "wade", einseitig=True, kg_anteil=0.85, wdh_min=12, wdh_max=25, pause_s=60,
       ausfuehrung="Auf einer Stufe, Ferse tief absenken. Der volle Weg ist "
                   "wichtiger als das Gewicht."),
    _u("Wadenheben sitzend", "Beine", "Kurzhantel",
       {"soleus": 1.0, "gastrocnemius": 0.4},
       "wade", benoetigt=("kurzhantel", "stuhl"), wdh_min=15, wdh_max=25, pause_s=45,
       ausfuehrung="Sitzend mit gebeugtem Knie. Nur so kommt der Schollenmuskel "
                   "unter dem Zwillingsmuskel überhaupt an die Reihe."),
    _u("Step-Ups", "Beine", "Körpergewicht",
       {"rectus_femoris": 1.0, "gluteus_maximus": 0.9, "vastus_lateralis": 0.8,
        "gluteus_medius": 0.5, "biceps_femoris": 0.4},
       "ausfallschritt", benoetigt=("stuhl",), einseitig=True, kg_anteil=0.75,
       wdh_min=10, wdh_max=20, pause_s=75),
    _u("Seitliche Ausfallschritte", "Beine", "Körpergewicht",
       {"adduktoren": 1.0, "gluteus_medius": 0.8, "vastus_medialis": 0.7,
        "gluteus_maximus": 0.6},
       "ausfallschritt", einseitig=True, kg_anteil=0.70,
       wdh_min=10, wdh_max=20, pause_s=60),

    # --- Kurzhantel ---
    _u("Goblet-Kniebeugen", "Beine", "Kurzhantel",
       {"rectus_femoris": 1.0, "vastus_lateralis": 1.0, "vastus_medialis": 1.0,
        "gluteus_maximus": 0.8, "adduktoren": 0.5, "bauch_oben": 0.4,
        "erector_spinae": 0.4},
       "beugen_knie", benoetigt=("kurzhantel",), grunduebung=True,
       wdh_min=8, wdh_max=15, pause_s=120,
       ausfuehrung="Eine Hantel vor der Brust. Das Gegengewicht hilft, aufrecht "
                   "zu bleiben, und macht sie zur besten Kniebeuge für zu Hause."),
    _u("Kurzhantel-Ausfallschritte", "Beine", "Kurzhantel",
       {"rectus_femoris": 1.0, "gluteus_maximus": 0.9, "vastus_lateralis": 0.8,
        "biceps_femoris": 0.4, "unterarm_beuger": 0.3},
       "ausfallschritt", benoetigt=("kurzhantel",), grunduebung=True,
       einseitig=True, wdh_min=8, wdh_max=15, pause_s=90),
    _u("Kurzhantel-Kreuzheben rumänisch", "Beine", "Kurzhantel",
       {"biceps_femoris": 1.0, "semitendinosus": 1.0, "gluteus_maximus": 0.9,
        "erector_spinae": 0.7, "unterarm_beuger": 0.4},
       "hueftstreckung", benoetigt=("kurzhantel",), grunduebung=True,
       wdh_min=8, wdh_max=15, pause_s=120,
       ausfuehrung="Knie leicht gebeugt und fest, Hüfte nach hinten schieben, "
                   "Hanteln dicht am Bein. Bis die Dehnung kommt, nicht tiefer.",
       fehler="Runder Rücken oder Knie beugen. Es ist eine Hüftbewegung, keine Kniebeuge."),
    _u("Einbeiniges Kreuzheben", "Beine", "Kurzhantel",
       {"biceps_femoris": 1.0, "gluteus_maximus": 0.9, "gluteus_medius": 0.7,
        "erector_spinae": 0.6, "semitendinosus": 0.7},
       "hueftstreckung", benoetigt=("kurzhantel",), einseitig=True,
       wdh_min=8, wdh_max=15, pause_s=90),
    _u("Kurzhantel-Bulgarische Kniebeugen", "Beine", "Kurzhantel",
       {"rectus_femoris": 1.0, "gluteus_maximus": 1.0, "vastus_lateralis": 0.9,
        "vastus_medialis": 0.9, "gluteus_medius": 0.6, "adduktoren": 0.5},
       "ausfallschritt", benoetigt=("kurzhantel", "stuhl"), grunduebung=True,
       einseitig=True, wdh_min=8, wdh_max=15, pause_s=120),
    _u("Kurzhantel-Wadenheben", "Beine", "Kurzhantel",
       {"gastrocnemius": 1.0, "soleus": 0.6},
       "wade", benoetigt=("kurzhantel",), wdh_min=12, wdh_max=20, pause_s=60),
    _u("Kurzhantel-Hip-Thrusts", "Beine", "Kurzhantel",
       {"gluteus_maximus": 1.0, "biceps_femoris": 0.6, "semitendinosus": 0.5},
       "hueftstreckung", benoetigt=("kurzhantel", "stuhl"),
       wdh_min=10, wdh_max=20, pause_s=90),

    # --- Studio ---
    _u("Kniebeugen", "Beine", "Langhantel",
       {"vastus_lateralis": 1.0, "vastus_medialis": 1.0, "rectus_femoris": 0.9,
        "vastus_intermedius": 0.9, "gluteus_maximus": 0.9, "adduktoren": 0.6,
        "erector_spinae": 0.7, "biceps_femoris": 0.4, "transversus": 0.5},
       "beugen_knie", benoetigt=("langhantel", "rack"), grunduebung=True,
       wdh_min=3, wdh_max=10, pause_s=210),
    _u("Frontkniebeugen", "Beine", "Langhantel",
       {"rectus_femoris": 1.0, "vastus_lateralis": 1.0, "vastus_medialis": 1.0,
        "gluteus_maximus": 0.7, "erector_spinae": 0.7, "bauch_oben": 0.5,
        "trapez_oben": 0.4},
       "beugen_knie", benoetigt=("langhantel", "rack"), grunduebung=True,
       wdh_min=4, wdh_max=10, pause_s=180),
    _u("Rumänisches Kreuzheben", "Beine", "Langhantel",
       {"biceps_femoris": 1.0, "semitendinosus": 1.0, "gluteus_maximus": 0.9,
        "erector_spinae": 0.8, "unterarm_beuger": 0.4},
       "hueftstreckung", benoetigt=("langhantel",), grunduebung=True,
       wdh_min=6, wdh_max=12, pause_s=150),
    _u("Hip Thrusts", "Beine", "Langhantel",
       {"gluteus_maximus": 1.0, "biceps_femoris": 0.6, "vastus_lateralis": 0.4},
       "hueftstreckung", benoetigt=("langhantel", "bank"),
       wdh_min=8, wdh_max=15, pause_s=120),
    _u("Beinpresse", "Beine", "Maschine",
       {"vastus_lateralis": 1.0, "vastus_medialis": 1.0, "gluteus_maximus": 0.8,
        "rectus_femoris": 0.7, "adduktoren": 0.5},
       "beugen_knie", benoetigt=("beinpresse",), wdh_min=8, wdh_max=20, pause_s=120),
    _u("Beinstrecker", "Beine", "Maschine",
       {"rectus_femoris": 1.0, "vastus_lateralis": 1.0, "vastus_medialis": 1.0,
        "vastus_intermedius": 0.9},
       "beugen_knie", benoetigt=("beinstrecker",), wdh_min=10, wdh_max=20, pause_s=75),
    _u("Beinbeuger", "Beine", "Maschine",
       {"biceps_femoris": 1.0, "semitendinosus": 1.0, "gastrocnemius": 0.4},
       "hueftstreckung", benoetigt=("beinbeuger",), wdh_min=10, wdh_max=20, pause_s=75),
    _u("Wadenheben stehend", "Beine", "Maschine",
       {"gastrocnemius": 1.0, "soleus": 0.6},
       "wade", benoetigt=("wadenmaschine",), wdh_min=10, wdh_max=20, pause_s=60),
]


# ===========================================================================
# RUMPF
# ===========================================================================

_RUMPF = [
    _u("Plank", "Rumpf", "Körpergewicht",
       {"transversus": 1.0, "bauch_oben": 0.8, "bauch_unten": 0.7,
        "obliquus_extern": 0.5, "delta_vorne": 0.4, "erector_spinae": 0.3,
        "gluteus_maximus": 0.4},
       "halten", kg_anteil=0.55, ist_zeit=True, reihe="plank", stufe=1,
       wdh_min=20, wdh_max=120, pause_s=60,
       ausfuehrung="Unterarme unter den Schultern, Körper eine Linie, Gesäß und "
                   "Bauch fest.",
       fehler="Hüfte zu hoch. Sieht stabil aus und nimmt dem Bauch die Arbeit ab."),
    _u("Seitlicher Plank", "Rumpf", "Körpergewicht",
       {"obliquus_extern": 1.0, "obliquus_intern": 0.9, "quadratus_lumborum": 0.7,
        "gluteus_medius": 0.6, "transversus": 0.6},
       "halten", einseitig=True, kg_anteil=0.50, ist_zeit=True,
       reihe="plank", stufe=2, wdh_min=20, wdh_max=90, pause_s=45),
    _u("Hollow Hold", "Rumpf", "Körpergewicht",
       {"bauch_unten": 1.0, "bauch_oben": 0.9, "transversus": 0.8,
        "hueftbeuger": 0.6},
       "halten", kg_anteil=0.40, ist_zeit=True, reihe="plank", stufe=3,
       wdh_min=15, wdh_max=60, pause_s=60,
       ausfuehrung="Rückenlage, Lende in den Boden gedrückt, Schultern und Beine "
                   "angehoben. Die Grundposition des Turnens."),
    _u("Crunches", "Rumpf", "Körpergewicht",
       {"bauch_oben": 1.0, "bauch_unten": 0.4, "obliquus_extern": 0.3},
       "rumpfbeugen", kg_anteil=0.25, wdh_min=15, wdh_max=30, pause_s=45),
    _u("Beinheben liegend", "Rumpf", "Körpergewicht",
       {"bauch_unten": 1.0, "hueftbeuger": 0.8, "bauch_oben": 0.5,
        "transversus": 0.5},
       "beinheben", kg_anteil=0.35, wdh_min=10, wdh_max=25, pause_s=60,
       ausfuehrung="Rückenlage, Hände unter dem Gesäß, Beine gestreckt heben und "
                   "kontrolliert senken.",
       fehler="Lende hebt vom Boden ab. Dann ist der Bauch aus dem Spiel."),
    _u("Beinheben hängend", "Rumpf", "Körpergewicht",
       {"bauch_unten": 1.0, "hueftbeuger": 0.8, "bauch_oben": 0.6,
        "unterarm_beuger": 0.5, "latissimus": 0.3},
       "beinheben", benoetigt=("klimmzugstange",), kg_anteil=0.45,
       wdh_min=8, wdh_max=20, pause_s=90,
       ausfuehrung="An der Stange hängend Knie oder gestreckte Beine anheben. "
                   "Gestreckt ist deutlich schwerer.",
       fehler="Schwung holen. Das Becken muss sich einrollen, sonst ist es "
              "reine Hüftbeuger-Arbeit."),
    _u("Toes to Bar", "Rumpf", "Körpergewicht",
       {"bauch_unten": 1.0, "bauch_oben": 0.8, "hueftbeuger": 0.7,
        "latissimus": 0.5, "unterarm_beuger": 0.5},
       "beinheben", benoetigt=("klimmzugstange",), kg_anteil=0.55,
       wdh_min=5, wdh_max=15, pause_s=90),
    _u("Russian Twists", "Rumpf", "Körpergewicht",
       {"obliquus_extern": 1.0, "obliquus_intern": 0.9, "bauch_oben": 0.5,
        "transversus": 0.4},
       "rotation", kg_anteil=0.30, wdh_min=15, wdh_max=30, pause_s=45),
    _u("Bauchroller", "Rumpf", "Körpergewicht",
       {"bauch_oben": 1.0, "bauch_unten": 0.9, "transversus": 0.9,
        "latissimus": 0.5, "erector_spinae": 0.4, "delta_vorne": 0.3},
       "halten", benoetigt=("ab_rad",), kg_anteil=0.60,
       wdh_min=5, wdh_max=15, pause_s=90,
       ausfuehrung="Kniend ausrollen, so weit die Kontrolle reicht.",
       fehler="Hohlkreuz beim Ausrollen. Das ist die Grenze, nicht der Boden."),
    _u("Mountain Climbers", "Rumpf", "Körpergewicht",
       {"bauch_unten": 1.0, "hueftbeuger": 0.8, "transversus": 0.7,
        "delta_vorne": 0.4, "herz_kreislauf": 0.6},
       "beinheben", kg_anteil=0.40, ist_zeit=True,
       wdh_min=20, wdh_max=60, pause_s=45),
    _u("Dead Bug", "Rumpf", "Körpergewicht",
       {"transversus": 1.0, "bauch_unten": 0.8, "bauch_oben": 0.5},
       "beinheben", kg_anteil=0.20, wdh_min=10, wdh_max=20, pause_s=45,
       ausfuehrung="Rückenlage, gegenüberliegender Arm und Bein strecken, Lende "
                   "bleibt am Boden. Die sicherste Übung für den tiefen Bauchmuskel."),
    _u("Bird Dog", "Rumpf", "Körpergewicht",
       {"erector_spinae": 1.0, "transversus": 0.7, "gluteus_maximus": 0.6,
        "delta_hinten": 0.3},
       "halten", kg_anteil=0.20, wdh_min=10, wdh_max=20, pause_s=45),
    _u("Cable Woodchops", "Rumpf", "Kabelzug",
       {"obliquus_extern": 1.0, "obliquus_intern": 0.9, "transversus": 0.6,
        "delta_vorne": 0.3},
       "rotation", benoetigt=("kabelzug",), wdh_min=12, wdh_max=20, pause_s=60),
    _u("Band-Pallof-Press", "Rumpf", "Band",
       {"obliquus_extern": 1.0, "transversus": 0.9, "obliquus_intern": 0.8},
       "rotation", benoetigt=("band",), einseitig=True, ist_zeit=True,
       wdh_min=15, wdh_max=45, pause_s=45,
       ausfuehrung="Band seitlich, vor der Brust wegdrücken und gegen die Drehung "
                   "halten. Rumpfarbeit ohne jede Bewegung."),
    _u("Kurzhantel-Seitbeugen", "Rumpf", "Kurzhantel",
       {"quadratus_lumborum": 1.0, "obliquus_extern": 0.9, "obliquus_intern": 0.7},
       "rotation", benoetigt=("kurzhantel",), einseitig=True,
       wdh_min=12, wdh_max=20, pause_s=45),
]


# ===========================================================================
# CARDIO
# ===========================================================================

_CARDIO = [
    _u("Seilspringen", "Cardio", "Körpergewicht",
       {"herz_kreislauf": 1.0, "gastrocnemius": 0.7, "soleus": 0.6,
        "unterarm_beuger": 0.3},
       "cardio", benoetigt=("springseil",), ist_zeit=True,
       wdh_min=60, wdh_max=600, pause_s=60),
    _u("Burpees", "Cardio", "Körpergewicht",
       {"herz_kreislauf": 1.0, "brust_mitte": 0.5, "rectus_femoris": 0.6,
        "gluteus_maximus": 0.5, "delta_vorne": 0.4, "bauch_oben": 0.4},
       "cardio", kg_anteil=0.70, wdh_min=8, wdh_max=25, pause_s=75),
    _u("Hampelmänner", "Cardio", "Körpergewicht",
       {"herz_kreislauf": 1.0, "delta_seite": 0.4, "gastrocnemius": 0.5},
       "cardio", ist_zeit=True, wdh_min=30, wdh_max=180, pause_s=45),
    _u("Hohe Kniehebeläufe", "Cardio", "Körpergewicht",
       {"herz_kreislauf": 1.0, "hueftbeuger": 0.7, "rectus_femoris": 0.5,
        "gastrocnemius": 0.5},
       "cardio", ist_zeit=True, wdh_min=30, wdh_max=120, pause_s=45),
    _u("Treppenlaufen", "Cardio", "Körpergewicht",
       {"herz_kreislauf": 1.0, "rectus_femoris": 0.7, "gluteus_maximus": 0.7,
        "gastrocnemius": 0.6},
       "cardio", ist_zeit=True, wdh_min=120, wdh_max=900, pause_s=90),
    _u("Laufband", "Cardio", "Maschine",
       {"herz_kreislauf": 1.0, "rectus_femoris": 0.4, "gastrocnemius": 0.5},
       "cardio", benoetigt=("laufband",), ist_zeit=True,
       wdh_min=600, wdh_max=3600, pause_s=0),
    _u("Rudergerät", "Cardio", "Maschine",
       {"herz_kreislauf": 1.0, "latissimus": 0.6, "rectus_femoris": 0.6,
        "erector_spinae": 0.5, "rhomboiden": 0.5},
       "cardio", benoetigt=("rudergeraet",), ist_zeit=True,
       wdh_min=600, wdh_max=2400, pause_s=0),
    _u("Ergometer", "Cardio", "Maschine",
       {"herz_kreislauf": 1.0, "rectus_femoris": 0.6, "gastrocnemius": 0.4},
       "cardio", benoetigt=("ergometer",), ist_zeit=True,
       wdh_min=600, wdh_max=3600, pause_s=0),
]


# ===========================================================================
# DEHNUNG UND MOBILITAET
# ===========================================================================

_DEHNUNG = [
    _u("Brustdehnung an der Wand", "Dehnung", "Körpergewicht",
       {"brust_mitte": 1.0, "delta_vorne": 0.6}, "dehnen",
       benoetigt=("wand",), ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Brustdehnung liegend", "Dehnung", "Körpergewicht",
       {"brust_mitte": 1.0, "delta_vorne": 0.7}, "dehnen",
       ist_zeit=True, wdh_min=30, wdh_max=90, pause_s=15),
    _u("Schulterdehnung Türrahmen", "Dehnung", "Körpergewicht",
       {"brust_oben": 1.0, "delta_vorne": 0.8}, "dehnen",
       benoetigt=("tuerrahmen",), ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Schulterdehnung quer", "Dehnung", "Körpergewicht",
       {"delta_hinten": 1.0, "latissimus": 0.3}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Überkopf-Trizepsdehnung", "Dehnung", "Körpergewicht",
       {"trizeps_lang": 1.0, "latissimus": 0.4}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Bizeps-Wanddehnung", "Dehnung", "Körpergewicht",
       {"bizeps_lang": 1.0, "delta_vorne": 0.5, "brust_mitte": 0.4}, "dehnen",
       benoetigt=("wand",), einseitig=True, ist_zeit=True,
       wdh_min=20, wdh_max=45, pause_s=15),
    _u("Unterarm-Beugerdehnung", "Dehnung", "Körpergewicht",
       {"unterarm_beuger": 1.0}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Unterarm-Streckerdehnung", "Dehnung", "Körpergewicht",
       {"unterarm_strecker": 1.0}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Latissimus-Dehnung seitlich", "Dehnung", "Körpergewicht",
       {"latissimus": 1.0, "obliquus_extern": 0.5, "teres_major": 0.5}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Kindshaltung", "Dehnung", "Körpergewicht",
       {"latissimus": 1.0, "erector_spinae": 0.8, "trapez_unten": 0.4}, "dehnen",
       ist_zeit=True, wdh_min=30, wdh_max=120, pause_s=15),
    _u("Katzenbuckel", "Dehnung", "Körpergewicht",
       {"erector_spinae": 1.0, "transversus": 0.4}, "dehnen",
       wdh_min=8, wdh_max=15, pause_s=15),
    _u("Kobra-Dehnung", "Dehnung", "Körpergewicht",
       {"bauch_oben": 1.0, "bauch_unten": 0.7, "hueftbeuger": 0.5}, "dehnen",
       ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Drehsitz (Wirbelsäulen-Rotation)", "Dehnung", "Körpergewicht",
       {"obliquus_extern": 1.0, "erector_spinae": 0.7, "gluteus_maximus": 0.5},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Seitliche Rumpfdehnung stehend", "Dehnung", "Körpergewicht",
       {"obliquus_extern": 1.0, "quadratus_lumborum": 0.8, "latissimus": 0.5},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Nackendehnung seitlich", "Dehnung", "Körpergewicht",
       {"trapez_oben": 1.0, "nacken": 0.8}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Oberer-Trapez-Dehnung", "Dehnung", "Körpergewicht",
       {"trapez_oben": 1.0, "nacken": 0.6}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=45, pause_s=15),
    _u("Quad-Dehnung stehend", "Dehnung", "Körpergewicht",
       {"rectus_femoris": 1.0, "vastus_lateralis": 0.6, "hueftbeuger": 0.5},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Hüftbeuger-Dehnung (Ausfallschritt)", "Dehnung", "Körpergewicht",
       {"hueftbeuger": 1.0, "rectus_femoris": 0.7, "gluteus_maximus": 0.3},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=30, wdh_max=90, pause_s=15),
    _u("Beinrückseiten-Dehnung stehend", "Dehnung", "Körpergewicht",
       {"biceps_femoris": 1.0, "semitendinosus": 0.9, "gastrocnemius": 0.4},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),
    _u("Beinrückseiten-Dehnung sitzend", "Dehnung", "Körpergewicht",
       {"biceps_femoris": 1.0, "semitendinosus": 0.9, "erector_spinae": 0.4},
       "dehnen", ist_zeit=True, wdh_min=30, wdh_max=90, pause_s=15),
    _u("Adduktoren-Dehnung sitzend", "Dehnung", "Körpergewicht",
       {"adduktoren": 1.0, "gluteus_medius": 0.3}, "dehnen",
       ist_zeit=True, wdh_min=30, wdh_max=90, pause_s=15),
    _u("Gesäßdehnung liegend (Piriformis)", "Dehnung", "Körpergewicht",
       {"gluteus_maximus": 1.0, "gluteus_medius": 0.8}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=30, wdh_max=90, pause_s=15),
    _u("Tauben-Pose", "Dehnung", "Körpergewicht",
       {"gluteus_maximus": 1.0, "gluteus_medius": 0.7, "hueftbeuger": 0.5},
       "dehnen", einseitig=True, ist_zeit=True, wdh_min=30, wdh_max=120, pause_s=15),
    _u("Wadendehnung an der Wand", "Dehnung", "Körpergewicht",
       {"gastrocnemius": 1.0, "soleus": 0.5}, "dehnen",
       benoetigt=("wand",), einseitig=True, ist_zeit=True,
       wdh_min=20, wdh_max=60, pause_s=15),
    _u("Schollenmuskel-Dehnung sitzend", "Dehnung", "Körpergewicht",
       {"soleus": 1.0, "gastrocnemius": 0.3}, "dehnen",
       einseitig=True, ist_zeit=True, wdh_min=20, wdh_max=60, pause_s=15),

    # --- Mobilitaet, neu ---
    _u("Schulterkreisen mit Band", "Mobilität", "Band",
       {"rotatorenmanschette": 1.0, "delta_hinten": 0.5, "brust_oben": 0.5},
       "rotation", benoetigt=("band",), wdh_min=8, wdh_max=15, pause_s=20,
       ausfuehrung="Band weit greifen, gestreckt über den Kopf nach hinten und "
                   "zurück. Öffnet die Schulter vor jedem Drücken."),
    _u("Hüftkreisen im Vierfüßlerstand", "Mobilität", "Körpergewicht",
       {"hueftbeuger": 1.0, "gluteus_medius": 0.6, "adduktoren": 0.5},
       "rotation", einseitig=True, wdh_min=8, wdh_max=15, pause_s=20),
    _u("Tiefe Hocke halten", "Mobilität", "Körpergewicht",
       {"adduktoren": 1.0, "gluteus_maximus": 0.6, "soleus": 0.6,
        "erector_spinae": 0.4},
       "halten", ist_zeit=True, wdh_min=30, wdh_max=180, pause_s=30,
       ausfuehrung="Einfach ganz unten sitzen bleiben. Die beste Vorbereitung "
                   "auf jede Kniebeuge und Gegenmittel zum Sitzen am Schreibtisch."),
    _u("Weltgrößte Dehnung", "Mobilität", "Körpergewicht",
       {"hueftbeuger": 1.0, "adduktoren": 0.7, "brust_mitte": 0.5,
        "erector_spinae": 0.5, "obliquus_extern": 0.5},
       "dehnen", einseitig=True, wdh_min=5, wdh_max=10, pause_s=20,
       ausfuehrung="Aus dem Ausfallschritt den Ellenbogen zum Boden, dann zur "
                   "Decke öffnen. Deckt Hüfte, Brustwirbelsäule und Schulter ab."),
    _u("Skapula-Klimmzüge", "Mobilität", "Körpergewicht",
       {"trapez_unten": 1.0, "rhomboiden": 0.8, "latissimus": 0.5,
        "rotatorenmanschette": 0.4},
       "ziehen_vertikal", benoetigt=("klimmzugstange",), kg_anteil=1.0,
       wdh_min=8, wdh_max=15, pause_s=45,
       ausfuehrung="An der Stange hängen und nur die Schulterblätter nach unten "
                   "ziehen, Arme bleiben gestreckt. Bringt bei, womit jeder "
                   "Klimmzug beginnt."),
]


KATALOG: list[Katalogeintrag] = (
    _BRUST + _RUECKEN + _SCHULTERN + _ARME + _BEINE + _RUMPF + _CARDIO + _DEHNUNG
)


# Alte Namen, die es im Bestand gibt und die jetzt anders heissen. Der
# Abgleich benennt sie um, statt eine zweite Uebung daneben anzulegen: sonst
# haette ein Nutzer "Klimmzüge" mit Historie und "Klimmzüge Obergriff" ohne.
UMBENENNUNGEN: dict[str, str] = {
    "Klimmzüge": "Klimmzüge Obergriff",
    "Kurzhantelrudern": "Kurzhantelrudern einarmig",
    "Ausfallschritte": "Kurzhantel-Ausfallschritte",
    "Kurzhantel-Fliegende": "Kurzhantel-Fliegende",
    "Beinheben hängend": "Beinheben hängend",
}


def nach_name() -> dict[str, Katalogeintrag]:
    return {e.name: e for e in KATALOG}


def bewegungsmuster() -> set[str]:
    return {e.muster for e in KATALOG}
