"""Die Muskulatur als Registry: Gruppe, Muskel, Volumen-Landmarks.

Warum das hier steht und nicht mehr in ``muscle_map.py``
--------------------------------------------------------

Die alte Karte kannte zehn Regionen und bildete jeden Muskelnamen aus dem
Katalog stumpf auf eine davon ab. Praktisch hiess das: "Quadrizeps",
"Adduktoren" und "Hueftbeuger" landeten alle auf ``quads``. Wer im Koerperbild
den Vastus medialis antippte, bekam dieselbe Uebungsliste wie beim Antippen des
ganzen Oberschenkels, weil es unterhalb der Region nichts gab, wonach sich
filtern liesse. Genau das war der Befund: die Auswahl war da, sie fuehrte nur
nirgendwo hin.

Jetzt drei Ebenen statt einer:

``REGIONEN`` (10)
    Die grobe Karte und die Push/Pull/Legs-Einteilung. Bleibt, damit die
    bestehende Frische-Ansicht und die Bestandsdaten weiter funktionieren.

``GRUPPEN`` (19)
    Die Einheit, in der Training geplant und Volumen gezaehlt wird. Hier
    haengen die Landmarks MEV/MAV/MRV, weil die Literatur sie so angibt:
    Saetze pro Woche fuer "Seitliche Schulter", nicht fuer "Schultern" und
    nicht fuer "Deltoideus lateralis".

``MUSKELN`` (44)
    Die anatomische Feinheit, die man im Koerperbild anfassen kann. Ein
    Uebung traegt ihre Anteile auf dieser Ebene, alles darueber wird
    aufsummiert. Deshalb unterscheiden sich die Listen fuer Vastus medialis
    und Rectus femoris jetzt wirklich.

Die Zahlen zu den Landmarks
---------------------------

MV/MEV/MAV/MRV in harten Saetzen je Woche, nach den Volumen-Landmarks von
Renaissance Periodization (Israetel). Was sie bedeuten:

* ``mv``  Erhaltung: darunter verliert man Substanz.
* ``mev`` ab hier waechst ueberhaupt etwas. Startwert eines Blocks.
* ``mav`` der Bereich, in dem der Zuwachs am besten ist. Zwei Zahlen, weil es
          ein Korridor ist und kein Punkt.
* ``mrv`` mehr kann man nicht mehr wegstecken. Darueber sammelt sich Ermuedung.

★ Diese Werte sind Richtwerte fuer einen fortgeschrittenen Anfaenger und
bewusst nicht als Wahrheit ausgewiesen. Sie verschieben sich mit Erfahrung,
Schlaf, Kaloriendefizit und Lebensstress. Die App zeigt sie deshalb als
Korridor mit Begruendung an und nicht als Zielvorgabe, die man "erfuellt".

★★ Gezaehlt werden nur Saetze nahe am Muskelversagen (0 bis 4 RIR). Ein
Aufwaermsatz zaehlt nicht, und ein Satz mit 8 Wiederholungen im Tank zaehlt
auch nicht. Das steht in ``satzzaehlung.py``, nicht hier.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Ebene 1: Regionen (grobe Karte, Push/Pull/Legs)
# ---------------------------------------------------------------------------

REGIONEN: dict[str, str] = {
    "chest": "Brust",
    "back": "Rücken",
    "traps": "Trapez",
    "shoulders": "Schultern",
    "biceps": "Bizeps",
    "triceps": "Trizeps",
    "quads": "Oberschenkel vorne",
    "hamstrings": "Oberschenkel hinten",
    "calves": "Waden",
    "core": "Rumpf",
}


# ---------------------------------------------------------------------------
# Ebene 2: Muskelgruppen mit Volumen-Landmarks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Gruppe:
    """Eine Muskelgruppe: die Einheit, in der Volumen geplant wird."""

    id: str
    name: str
    region: str
    ppl: str                    # push | pull | legs | core
    mv: int                     # Erhaltungsvolumen
    mev: int                    # Minimal wirksames Volumen
    mav_min: int                # Korridor bester Zuwachs, untere Grenze
    mav_max: int                # Korridor bester Zuwachs, obere Grenze
    mrv: int                    # Maximal verkraftbares Volumen
    # Wie lange die Gruppe nach einem harten Reiz braucht, bis sie wieder
    # voll belastbar ist. Grundlage der Frischeanzeige und der Vorschlaege.
    # Grosse Gruppen mit langen Hebeln brauchen laenger als kleine.
    erholung_stunden: int = 48


GRUPPEN: dict[str, Gruppe] = {g.id: g for g in [
    # --- Oberkoerper druecken ---
    Gruppe("brust", "Brust", "chest", "push",
           mv=4, mev=8, mav_min=12, mav_max=20, mrv=22, erholung_stunden=48),
    Gruppe("front_delta", "Vordere Schulter", "shoulders", "push",
           # ★ MEV 0 ist kein Tippfehler: die vordere Schulter bekommt bei
           # jedem Druecken so viel indirekte Arbeit ab, dass sie ohne eine
           # einzige gezielte Uebung waechst. Wer sie trotzdem direkt
           # traniert, kommt schnell an die Grenze.
           mv=0, mev=0, mav_min=6, mav_max=8, mrv=12, erholung_stunden=36),
    Gruppe("seit_delta", "Seitliche Schulter", "shoulders", "push",
           mv=6, mev=8, mav_min=16, mav_max=22, mrv=26, erholung_stunden=24),
    Gruppe("trizeps", "Trizeps", "triceps", "push",
           mv=4, mev=6, mav_min=10, mav_max=14, mrv=18, erholung_stunden=36),

    # --- Oberkoerper ziehen ---
    Gruppe("latissimus", "Latissimus", "back", "pull",
           mv=6, mev=10, mav_min=14, mav_max=22, mrv=25, erholung_stunden=48),
    Gruppe("oberer_ruecken", "Oberer Rücken", "back", "pull",
           mv=4, mev=8, mav_min=12, mav_max=20, mrv=25, erholung_stunden=48),
    Gruppe("trapez", "Trapez", "traps", "pull",
           mv=0, mev=4, mav_min=12, mav_max=20, mrv=26, erholung_stunden=36),
    Gruppe("hinter_delta", "Hintere Schulter", "shoulders", "pull",
           mv=0, mev=6, mav_min=12, mav_max=20, mrv=26, erholung_stunden=24),
    Gruppe("bizeps", "Bizeps", "biceps", "pull",
           mv=4, mev=8, mav_min=14, mav_max=20, mrv=26, erholung_stunden=36),
    Gruppe("unterarm", "Unterarm", "biceps", "pull",
           mv=2, mev=4, mav_min=8, mav_max=12, mrv=16, erholung_stunden=24),

    # --- Beine ---
    Gruppe("quadrizeps", "Quadrizeps", "quads", "legs",
           mv=6, mev=8, mav_min=12, mav_max=18, mrv=20, erholung_stunden=72),
    Gruppe("beinbizeps", "Beinbizeps", "hamstrings", "legs",
           mv=3, mev=4, mav_min=10, mav_max=16, mrv=20, erholung_stunden=72),
    Gruppe("gesaess", "Gesäß", "hamstrings", "legs",
           mv=0, mev=4, mav_min=12, mav_max=16, mrv=16, erholung_stunden=48),
    Gruppe("adduktoren", "Adduktoren", "quads", "legs",
           mv=0, mev=4, mav_min=8, mav_max=12, mrv=16, erholung_stunden=48),
    Gruppe("waden", "Waden", "calves", "legs",
           mv=6, mev=8, mav_min=12, mav_max=16, mrv=20, erholung_stunden=24),

    # --- Rumpf ---
    Gruppe("bauch", "Bauch", "core", "core",
           mv=0, mev=0, mav_min=16, mav_max=20, mrv=25, erholung_stunden=24),
    Gruppe("unterer_ruecken", "Unterer Rücken", "core", "core",
           # ★ MRV bewusst niedrig: der untere Ruecken bekommt bei Kreuzheben,
           # Kniebeugen und Rudern so viel ab, dass direktes Volumen schnell
           # zu viel wird. Er ist die Gruppe, die am haeufigsten unbemerkt
           # ueberlastet ist, weil kaum jemand ihre Saetze zaehlt.
           mv=0, mev=2, mav_min=4, mav_max=8, mrv=12, erholung_stunden=72),
    Gruppe("hueftbeuger", "Hüftbeuger", "core", "core",
           mv=0, mev=2, mav_min=6, mav_max=10, mrv=14, erholung_stunden=48),
    Gruppe("nacken", "Nacken", "traps", "pull",
           mv=0, mev=4, mav_min=8, mav_max=12, mrv=16, erholung_stunden=36),
]}


# ---------------------------------------------------------------------------
# Ebene 3: Einzelmuskeln
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Muskel:
    """Ein einzelner Muskel oder Muskelkopf.

    ``ansicht`` sagt, von welcher Seite man ihn sieht. Das Koerpermodell
    braucht das, um beim Anwaehlen von hinten nicht nach vorne zu drehen.
    """

    id: str
    name: str                   # Alltagsname, so steht er in der Oberflaeche
    fachname: str               # Terminologia Anatomica, fuer die Detailseite
    gruppe: str
    ansicht: str                # vorne | hinten | beide
    # Was der Muskel tut. Steht in der Uebungsauswahl unter dem Namen und
    # erklaert, warum eine Uebung ihn trifft und eine andere nicht.
    funktion: str = ""
    aliasse: tuple[str, ...] = field(default_factory=tuple)


def _m(id_: str, name: str, fachname: str, gruppe: str, ansicht: str,
       funktion: str = "", aliasse: tuple[str, ...] = ()) -> Muskel:
    return Muskel(id_, name, fachname, gruppe, ansicht, funktion, aliasse)


MUSKELN: dict[str, Muskel] = {m.id: m for m in [
    # --- Brust ---
    _m("brust_oben", "Obere Brust", "Pectoralis major, Pars clavicularis",
       "brust", "vorne", "Hebt den Arm nach vorne oben",
       ("Obere Brust",)),
    _m("brust_mitte", "Mittlere Brust", "Pectoralis major, Pars sternocostalis",
       "brust", "vorne", "Führt den Arm vor der Brust zusammen",
       ("Brust",)),
    _m("brust_unten", "Untere Brust", "Pectoralis major, Pars abdominalis",
       "brust", "vorne", "Zieht den Arm nach vorne unten"),

    # --- Schultern ---
    _m("delta_vorne", "Vordere Schulter", "Deltoideus, Pars clavicularis",
       "front_delta", "vorne", "Hebt den Arm nach vorne",
       ("Vordere Schulter", "Schultern")),
    _m("delta_seite", "Seitliche Schulter", "Deltoideus, Pars acromialis",
       "seit_delta", "beide", "Hebt den Arm zur Seite",
       ("Seitliche Schulter",)),
    _m("delta_hinten", "Hintere Schulter", "Deltoideus, Pars spinalis",
       "hinter_delta", "hinten", "Zieht den Arm nach hinten",
       ("Hintere Schulter",)),

    # --- Ruecken ---
    _m("latissimus", "Latissimus", "Latissimus dorsi",
       "latissimus", "hinten", "Zieht den Arm von oben nach unten an den Körper",
       ("Latissimus",)),
    _m("teres_major", "Großer Rundmuskel", "Teres major",
       "latissimus", "hinten", "Arbeitet beim Ziehen mit dem Latissimus"),
    _m("rhomboiden", "Rautenmuskeln", "Rhomboidei",
       "oberer_ruecken", "hinten", "Zieht die Schulterblätter zusammen"),
    _m("trapez_mitte", "Trapez Mitte", "Trapezius, Pars transversa",
       "oberer_ruecken", "hinten", "Zieht die Schulterblätter zusammen"),
    _m("trapez_oben", "Trapez oben", "Trapezius, Pars descendens",
       "trapez", "beide", "Hebt die Schultern",
       ("Trapez",)),
    _m("trapez_unten", "Trapez unten", "Trapezius, Pars ascendens",
       "trapez", "hinten", "Zieht die Schulterblätter nach unten"),
    _m("nacken", "Nacken", "Splenius capitis / Sternocleidomastoideus",
       "nacken", "beide", "Bewegt und stabilisiert den Kopf"),

    # --- Arme ---
    _m("bizeps_lang", "Bizeps langer Kopf", "Biceps brachii, Caput longum",
       "bizeps", "vorne", "Beugt den Arm, stärker bei zurückgeführtem Ellenbogen",
       ("Bizeps",)),
    _m("bizeps_kurz", "Bizeps kurzer Kopf", "Biceps brachii, Caput breve",
       "bizeps", "vorne", "Beugt den Arm, stärker bei vorgeführtem Ellenbogen"),
    _m("brachialis", "Armbeuger", "Brachialis",
       "bizeps", "vorne", "Beugt den Arm unabhängig von der Handstellung"),
    _m("trizeps_lang", "Trizeps langer Kopf", "Triceps brachii, Caput longum",
       "trizeps", "hinten", "Streckt den Arm, arbeitet über die Schulter mit",
       ("Trizeps",)),
    _m("trizeps_lateral", "Trizeps äußerer Kopf", "Triceps brachii, Caput laterale",
       "trizeps", "hinten", "Streckt den Arm, sichtbar an der Außenseite"),
    _m("trizeps_medial", "Trizeps innerer Kopf", "Triceps brachii, Caput mediale",
       "trizeps", "hinten", "Streckt den Arm, arbeitet in jedem Winkel mit"),
    _m("unterarm_beuger", "Unterarmbeuger", "Flexores antebrachii",
       "unterarm", "vorne", "Schließt die Hand, trägt die Griffkraft",
       ("Unterarm",)),
    _m("unterarm_strecker", "Unterarmstrecker", "Extensores antebrachii",
       "unterarm", "hinten", "Streckt Hand und Finger"),
    _m("brachioradialis", "Oberarmspeichenmuskel", "Brachioradialis",
       "unterarm", "vorne", "Beugt den Arm im Hammergriff"),

    # --- Beine vorne ---
    _m("rectus_femoris", "Gerader Oberschenkelmuskel", "Rectus femoris",
       "quadrizeps", "vorne", "Streckt das Knie und beugt die Hüfte",
       ("Quadrizeps",)),
    _m("vastus_lateralis", "Äußerer Schenkelmuskel", "Vastus lateralis",
       "quadrizeps", "vorne", "Streckt das Knie, formt die Außenseite"),
    _m("vastus_medialis", "Innerer Schenkelmuskel", "Vastus medialis",
       "quadrizeps", "vorne", "Streckt das Knie, arbeitet zuletzt am stärksten"),
    _m("vastus_intermedius", "Mittlerer Schenkelmuskel", "Vastus intermedius",
       "quadrizeps", "vorne", "Streckt das Knie, liegt unter dem Rectus femoris"),
    _m("adduktoren", "Adduktoren", "Adductores",
       "adduktoren", "vorne", "Führt das Bein zur Mitte, arbeitet bei tiefen Kniebeugen mit",
       ("Adduktoren",)),
    _m("hueftbeuger", "Hüftbeuger", "Iliopsoas",
       "hueftbeuger", "vorne", "Zieht das Knie nach oben",
       ("Hüftbeuger",)),

    # --- Beine hinten ---
    _m("biceps_femoris", "Beinbizeps außen", "Biceps femoris",
       "beinbizeps", "hinten", "Beugt das Knie und streckt die Hüfte",
       ("Beinbizeps",)),
    _m("semitendinosus", "Beinbizeps innen", "Semitendinosus / Semimembranosus",
       "beinbizeps", "hinten", "Beugt das Knie, dreht den Unterschenkel nach innen"),
    _m("gluteus_maximus", "Großer Gesäßmuskel", "Gluteus maximus",
       "gesaess", "hinten", "Streckt die Hüfte, der stärkste Muskel im Körper",
       ("Gesäß",)),
    _m("gluteus_medius", "Mittlerer Gesäßmuskel", "Gluteus medius / minimus",
       "gesaess", "hinten", "Führt das Bein zur Seite, hält das Becken gerade"),
    _m("gastrocnemius", "Zwillingswadenmuskel", "Gastrocnemius",
       "waden", "hinten", "Streckt den Fuß bei gestrecktem Knie",
       ("Waden",)),
    _m("soleus", "Schollenmuskel", "Soleus",
       "waden", "hinten", "Streckt den Fuß bei gebeugtem Knie"),

    # --- Rumpf ---
    _m("bauch_oben", "Oberer Bauch", "Rectus abdominis, oberer Anteil",
       "bauch", "vorne", "Beugt den Oberkörper nach vorne",
       ("Bauch", "Core")),
    _m("bauch_unten", "Unterer Bauch", "Rectus abdominis, unterer Anteil",
       "bauch", "vorne", "Zieht das Becken nach oben",
       ("Untere Bauchmuskeln",)),
    _m("obliquus_extern", "Äußerer schräger Bauchmuskel", "Obliquus externus abdominis",
       "bauch", "vorne", "Dreht und neigt den Oberkörper",
       ("Seitliche Bauchmuskeln",)),
    _m("obliquus_intern", "Innerer schräger Bauchmuskel", "Obliquus internus abdominis",
       "bauch", "vorne", "Dreht den Oberkörper zur gleichen Seite"),
    _m("transversus", "Querer Bauchmuskel", "Transversus abdominis",
       "bauch", "vorne", "Spannt die Bauchwand, stabilisiert die Wirbelsäule"),
    _m("erector_spinae", "Rückenstrecker", "Erector spinae",
       "unterer_ruecken", "hinten", "Streckt und hält die Wirbelsäule",
       ("Unterer Rücken", "Rückenstrecker")),
    _m("quadratus_lumborum", "Quadratischer Lendenmuskel", "Quadratus lumborum",
       "unterer_ruecken", "hinten", "Neigt den Rumpf zur Seite"),

    # --- Sonstiges ---
    _m("serratus", "Sägemuskel", "Serratus anterior",
       "brust", "vorne", "Schiebt das Schulterblatt nach vorne"),
    _m("rotatorenmanschette", "Rotatorenmanschette", "Supraspinatus / Infraspinatus / Teres minor / Subscapularis",
       "hinter_delta", "hinten", "Dreht und sichert das Schultergelenk"),
    _m("herz_kreislauf", "Herz-Kreislauf", "Systema cardiovasculare",
       "bauch", "beide", "Ausdauerleistung, kein einzelner Muskel",
       ("Herz-Kreislauf",)),
]}


# ---------------------------------------------------------------------------
# Abgeleitete Nachschlagetabellen
# ---------------------------------------------------------------------------

MUSKELN_JE_GRUPPE: dict[str, list[str]] = {}
for _mk in MUSKELN.values():
    MUSKELN_JE_GRUPPE.setdefault(_mk.gruppe, []).append(_mk.id)

GRUPPEN_JE_REGION: dict[str, list[str]] = {}
for _g in GRUPPEN.values():
    GRUPPEN_JE_REGION.setdefault(_g.region, []).append(_g.id)

MUSKELN_JE_REGION: dict[str, list[str]] = {}
for _g in GRUPPEN.values():
    MUSKELN_JE_REGION.setdefault(_g.region, []).extend(MUSKELN_JE_GRUPPE.get(_g.id, []))

# Alter Muskelname aus dem Bestandskatalog -> neue Muskel-Kennung.
# ★ Diese Tabelle ist der Uebergang, nicht der Dauerzustand: neue Uebungen
# tragen ihre Anteile direkt als Kennungen. Sie bleibt, weil ein Nutzer eigene
# Uebungen mit freien Muskelnamen angelegt haben kann und die nicht still
# aus der Auswertung fallen duerfen.
ALIAS_AUF_MUSKEL: dict[str, str] = {}
for _mk in MUSKELN.values():
    ALIAS_AUF_MUSKEL[_mk.name.lower()] = _mk.id
    ALIAS_AUF_MUSKEL[_mk.id] = _mk.id
    for _alias in _mk.aliasse:
        ALIAS_AUF_MUSKEL[_alias.lower()] = _mk.id

# Sammelbegriffe des Bestands, die auf mehrere Muskeln zeigen.
SAMMEL_ALIAS: dict[str, list[str]] = {
    "brust": ["brust_mitte", "brust_oben", "brust_unten"],
    "schultern": ["delta_vorne", "delta_seite", "delta_hinten"],
    "bizeps": ["bizeps_lang", "bizeps_kurz", "brachialis"],
    "trizeps": ["trizeps_lang", "trizeps_lateral", "trizeps_medial"],
    "quadrizeps": ["rectus_femoris", "vastus_lateralis", "vastus_medialis",
                   "vastus_intermedius"],
    "beinbizeps": ["biceps_femoris", "semitendinosus"],
    "gesäß": ["gluteus_maximus", "gluteus_medius"],
    "waden": ["gastrocnemius", "soleus"],
    "unterarm": ["unterarm_beuger", "unterarm_strecker", "brachioradialis"],
    "core": ["bauch_oben", "bauch_unten", "transversus"],
    "bauch": ["bauch_oben", "bauch_unten"],
    "seitliche bauchmuskeln": ["obliquus_extern", "obliquus_intern"],
    "untere bauchmuskeln": ["bauch_unten"],
    "trapez": ["trapez_oben", "trapez_mitte", "trapez_unten"],
    "latissimus": ["latissimus", "teres_major"],
    "unterer rücken": ["erector_spinae", "quadratus_lumborum"],
    "rückenstrecker": ["erector_spinae"],
    "beine": ["rectus_femoris", "vastus_lateralis", "vastus_medialis",
              "biceps_femoris", "gluteus_maximus", "gastrocnemius"],
    "ganzkörper": ["brust_mitte", "latissimus", "delta_seite", "rectus_femoris",
                   "gluteus_maximus", "bauch_oben", "erector_spinae"],
    "herz-kreislauf": ["herz_kreislauf"],
    "hüftbeuger": ["hueftbeuger"],
    "adduktoren": ["adduktoren"],
    "obere brust": ["brust_oben"],
    "vordere schulter": ["delta_vorne"],
    "seitliche schulter": ["delta_seite"],
    "hintere schulter": ["delta_hinten"],
}


def muskel_aufloesen(name: str) -> list[str]:
    """Freitext-Muskelname aus dem Bestand auf Kennungen abbilden.

    Gibt eine Liste zurueck, weil Sammelbegriffe wie "Beine" auf mehrere
    Muskeln zeigen. Unbekanntes ergibt eine leere Liste, und der Aufrufer
    entscheidet, ob das ein Fehler ist oder nur eine Eigenanlage ohne
    Zuordnung.
    """
    schluessel = (name or "").strip().lower()
    if not schluessel:
        return []
    if schluessel in SAMMEL_ALIAS:
        return list(SAMMEL_ALIAS[schluessel])
    treffer = ALIAS_AUF_MUSKEL.get(schluessel)
    return [treffer] if treffer else []


def gruppe_von_muskel(muskel_id: str) -> str | None:
    m = MUSKELN.get(muskel_id)
    return m.gruppe if m else None


def region_von_gruppe(gruppe_id: str) -> str | None:
    g = GRUPPEN.get(gruppe_id)
    return g.region if g else None


def region_von_muskel(muskel_id: str) -> str | None:
    g = gruppe_von_muskel(muskel_id)
    return region_von_gruppe(g) if g else None


PPL_JE_GRUPPE: dict[str, str] = {g.id: g.ppl for g in GRUPPEN.values()}

# Anteil, den eine ausgewogene Woche je Bewegungsrichtung haben sollte.
# Bleibt bei der bisherigen Aufteilung, damit die Balance-Anzeige vergleichbar
# bleibt.
IDEALER_PPL_ANTEIL: dict[str, float] = {
    "push": 0.30,
    "pull": 0.30,
    "legs": 0.30,
    "core": 0.10,
}
