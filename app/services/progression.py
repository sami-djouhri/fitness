"""Was beim naechsten Mal auf der Stange liegen sollte, und warum.

Das ist die Stelle, an der aus erfassten Saetzen eine Entscheidung wird. Sie
loest ``WorkoutService.get_overload_suggestion`` ab, die zwei Faelle kannte
("alle Ziel-Wiederholungen erreicht" gegen "gleiches Gewicht") und dabei die
Ziel-Wiederholung mit einer fest eingebauten 12 verglich, unabhaengig davon,
was im Plan stand.

Womit hier gerechnet wird
-------------------------

**1RM aus mehreren Formeln.** Der Bestand nutzte allein Epley. Die Formel
ueberschaetzt oberhalb von etwa zehn Wiederholungen deutlich. Hier laufen
drei Formeln parallel und der Median entscheidet, und ab 12 Wiederholungen
wird die Schaetzung ausdruecklich als unsicher gemeldet statt als Zahl
hingestellt.

**Doppelprogression mit RIR.** Der belastbarste Befund der Literatur zur
Trainingssteuerung ist nicht das ausgefeilteste Modell, sondern das
einfachste: wer den Abstand zum Muskelversagen einschaetzt und danach
steuert, wird staerker als wer festen Prozentzahlen folgt. Also: erst
Wiederholungen bis ans obere Ende des Zielbereichs, dann Gewicht hoch, und
das Ganze gebremst vom gemeldeten RIR.

★ RIR statt RPE nach aussen. Gespeichert wird weiter ``rpe``, weil daran die
Bestandsdaten haengen. ``RIR = 10 minus RPE``. Die Frage "wie viele haettest
du noch geschafft" beantwortet ein Mensch zuverlaessig, die Frage "wie
anstrengend war das von 1 bis 10" nicht.

**Plateau.** Drei Einheiten ohne Zuwachs im geschaetzten 1RM. Dann ist nicht
mehr Gewicht die Antwort, sondern eine Aenderung: andere Variante, mehr
Volumen, oder eine leichtere Woche.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Exercise, PlanExercise, Workout, WorkoutSet
from app.services.anteile import effektive_last
from app.services.satzfilter import arbeitssatz

# Ab hier ist eine 1RM-Schaetzung aus Wiederholungen nicht mehr belastbar.
# Die Formeln sind an Saetzen bis rund zehn Wiederholungen entwickelt.
WDH_GRENZE_SCHAETZUNG = 12

# So viele Einheiten ohne Zuwachs gelten als Plateau.
EINHEITEN_FUER_PLATEAU = 3

# Kleinster sinnvoller Sprung, wenn das Profil nichts anderes sagt.
STANDARD_SCHRITT_KG = 2.5


@dataclass
class Vorschlag:
    exercise_id: int
    exercise_name: str
    gewicht_kg: float | None
    wdh: int | None
    letztes_gewicht_kg: float | None
    letzte_wdh: int | None
    # steigern | wiederholen | wdh_steigern | reduzieren | einstieg | plateau
    art: str
    begruendung: str
    zielbereich: tuple[int, int]
    e1rm: float | None = None
    e1rm_unsicher: bool = False
    plateau_seit: int = 0


# ---------------------------------------------------------------------------
# 1RM
# ---------------------------------------------------------------------------

def epley(gewicht: float, wdh: int) -> float:
    return gewicht * (1 + wdh / 30)


def brzycki(gewicht: float, wdh: int) -> float:
    # Faellt oberhalb von 36 Wiederholungen auseinander (Nenner wird negativ).
    if wdh >= 36:
        return 0.0
    return gewicht * 36 / (37 - wdh)


def lombardi(gewicht: float, wdh: int) -> float:
    return gewicht * (wdh ** 0.10)


def geschaetztes_1rm(gewicht: float | None, wdh: int | None) -> tuple[float | None, bool]:
    """Median aus drei Formeln, plus die Angabe, ob man ihm trauen kann.

    Eine einzelne Formel liegt je nach Wiederholungszahl systematisch daneben:
    Epley zu hoch, Brzycki zu niedrig bei vielen Wiederholungen. Der Median
    aus dreien ist robuster als jede einzelne und deutlich einfacher als eine
    Anpassung, die aus den eigenen Daten lernt (dafuer braeuchte es Saetze mit
    ein bis drei Wiederholungen, die kaum jemand macht).
    """
    if not gewicht or not wdh or gewicht <= 0 or wdh <= 0:
        return None, False
    if wdh == 1:
        return round(float(gewicht), 1), False
    werte = [f(gewicht, wdh) for f in (epley, brzycki, lombardi)]
    werte = [w for w in werte if w > 0]
    if not werte:
        return None, False
    return round(statistics.median(werte), 1), wdh > WDH_GRENZE_SCHAETZUNG


def gewicht_fuer_wdh(e1rm: float, ziel_wdh: int) -> float:
    """Umkehrung: welches Gewicht passt zu so vielen Wiederholungen?

    Nach Epley aufgeloest. Wird fuer den Einstiegsvorschlag gebraucht, wenn zu
    einer Uebung noch nichts erfasst ist, aber eine verwandte Uebung schon.
    """
    if ziel_wdh <= 1:
        return round(e1rm, 1)
    return round(e1rm / (1 + ziel_wdh / 30), 1)


def rir_aus_rpe(rpe: float | None) -> float | None:
    if rpe is None:
        return None
    return round(10.0 - float(rpe), 1)


def rpe_aus_rir(rir: float | None) -> float | None:
    if rir is None:
        return None
    return round(10.0 - float(rir), 1)


def runden_auf_schritt(gewicht: float, schritt: float) -> float:
    """Auf das runden, was die vorhandene Ausruestung ueberhaupt hergibt.

    ★ Ohne das ist ein Vorschlag Zierde: wer verstellbare Kurzhanteln in
    2-kg-Stufen hat, kann 22,5 kg nicht einstellen und sucht dann nach dem
    Fehler bei sich.
    """
    if schritt <= 0:
        return round(gewicht, 1)
    return round(round(gewicht / schritt) * schritt, 2)


# ---------------------------------------------------------------------------
# Vorschlag
# ---------------------------------------------------------------------------

class ProgressionsService:
    def __init__(self, db: Session, gewichtsschritt_kg: float = STANDARD_SCHRITT_KG,
                 koerpergewicht_kg: float | None = None):
        self.db = db
        self.schritt = gewichtsschritt_kg or STANDARD_SCHRITT_KG
        self.koerpergewicht_kg = koerpergewicht_kg

    # -- Rohdaten ---------------------------------------------------------

    def _letzte_einheiten(self, exercise_id: int, anzahl: int = 5) -> list[list[WorkoutSet]]:
        """Die letzten Einheiten mit dieser Uebung, je als Liste ihrer Arbeitssaetze."""
        zeilen = (
            self.db.query(WorkoutSet, Workout.started_at)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(WorkoutSet.exercise_id == exercise_id, *arbeitssatz())
            .order_by(desc(Workout.started_at), WorkoutSet.set_number)
            .all()
        )
        je_workout: dict[int, list[WorkoutSet]] = {}
        reihenfolge: list[int] = []
        for satz, _start in zeilen:
            if satz.workout_id not in je_workout:
                je_workout[satz.workout_id] = []
                reihenfolge.append(satz.workout_id)
            je_workout[satz.workout_id].append(satz)
        return [je_workout[wid] for wid in reihenfolge[:anzahl]]

    def _zielbereich(self, exercise_id: int, uebung: Exercise) -> tuple[int, int]:
        """Der Wiederholungsbereich, der fuer diese Uebung gilt.

        Der Plan schlaegt den Katalog: wer im Plan 4 bis 6 eingetragen hat,
        meint das auch. Ohne Plan gilt, was am Katalogeintrag steht, und der
        unterscheidet sich je Uebung (Waden 12 bis 20, Kreuzheben 3 bis 8).
        Die alte Logik verglich stattdessen jede Uebung mit einer fest
        eingebauten 12.
        """
        pe = (
            self.db.query(PlanExercise)
            .filter(PlanExercise.exercise_id == exercise_id)
            .order_by(desc(PlanExercise.id))
            .first()
        )
        if pe:
            return pe.target_reps_min, pe.target_reps_max
        return uebung.wdh_min, uebung.wdh_max

    # -- Auswertung -------------------------------------------------------

    def plateau_laenge(self, exercise_id: int) -> int:
        """Wie viele Einheiten in Folge ohne Zuwachs im geschaetzten 1RM."""
        einheiten = self._letzte_einheiten(exercise_id, anzahl=6)
        if len(einheiten) < 2:
            return 0
        bestwerte: list[float] = []
        for saetze in einheiten:
            werte = [geschaetztes_1rm(s.weight_kg, s.reps)[0] or 0.0 for s in saetze]
            bestwerte.append(max(werte) if werte else 0.0)
        # bestwerte[0] ist die juengste Einheit.
        zaehler = 0
        for i in range(len(bestwerte) - 1):
            if bestwerte[i] <= bestwerte[i + 1]:
                zaehler += 1
            else:
                break
        return zaehler

    def vorschlag(self, exercise_id: int) -> Vorschlag:
        uebung = self.db.get(Exercise, exercise_id)
        if uebung is None:
            return Vorschlag(exercise_id, "", None, None, None, None,
                             "einstieg", "Übung nicht gefunden", (8, 12))

        unten, oben = self._zielbereich(exercise_id, uebung)
        einheiten = self._letzte_einheiten(exercise_id, anzahl=4)

        if not einheiten:
            return Vorschlag(
                exercise_id, uebung.name, None, unten, None, None,
                "einstieg",
                f"Noch nichts erfasst. Beginne mit einem Gewicht, bei dem {unten} "
                f"saubere Wiederholungen klar gehen, und trage danach ein, "
                f"wie viele noch drin gewesen wären.",
                (unten, oben),
            )

        letzte = einheiten[0]
        # Der schwerste Arbeitssatz der letzten Einheit ist die Bezugsgroesse.
        # Nicht der letzte: bei absteigenden Saetzen waere das der leichteste.
        bezug = max(letzte, key=lambda s: (s.weight_kg or 0, s.reps or 0))
        letztes_gewicht = bezug.weight_kg
        letzte_wdh = bezug.reps
        e1rm, unsicher = geschaetztes_1rm(letztes_gewicht, letzte_wdh)
        plateau = self.plateau_laenge(exercise_id)

        # RIR des schwersten Satzes, falls erfasst.
        rir = rir_aus_rpe(bezug.rpe)

        # Zeitbasierte Uebungen: Sekunden statt Gewicht steigern.
        if uebung.ist_zeit:
            dauer = bezug.duration_seconds or 0
            return Vorschlag(
                exercise_id, uebung.name, letztes_gewicht, dauer,
                letztes_gewicht, dauer,
                "wdh_steigern",
                f"Zuletzt {dauer} Sekunden. Halte {dauer + 5} und steigere in "
                f"Fünf-Sekunden-Schritten.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        # Koerpergewichtsuebung ohne Zusatzgewicht: Wiederholungen sind der
        # Hebel, bis das obere Ende erreicht ist. Danach Zusatzgewicht oder
        # die naechste Stufe der Reihe.
        reine_kg_uebung = uebung.kg_anteil > 0 and not letztes_gewicht

        alle_am_oberen_ende = all(
            (s.reps or 0) >= oben for s in letzte if (s.weight_kg or 0) == (letztes_gewicht or 0)
        )
        unter_dem_unteren_ende = (letzte_wdh or 0) < unten

        if plateau >= EINHEITEN_FUER_PLATEAU:
            return Vorschlag(
                exercise_id, uebung.name, letztes_gewicht, letzte_wdh,
                letztes_gewicht, letzte_wdh,
                "plateau",
                f"Seit {plateau} Einheiten kein Zuwachs. Mehr Gewicht ist hier "
                f"nicht die Antwort: eine Woche mit weniger Volumen, eine andere "
                f"Variante oder ein zusätzlicher Satz bringt mehr.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        if unter_dem_unteren_ende:
            neu = runden_auf_schritt(max(0.0, (letztes_gewicht or 0) - self.schritt),
                                     self.schritt)
            return Vorschlag(
                exercise_id, uebung.name, neu or None, unten,
                letztes_gewicht, letzte_wdh,
                "reduzieren",
                f"Zuletzt {letzte_wdh} Wiederholungen, das liegt unter dem Zielbereich "
                f"ab {unten}. Etwas leichter, dafür sauber im Bereich.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        if reine_kg_uebung:
            if alle_am_oberen_ende:
                naechste = self._naechste_stufe(uebung)
                if naechste:
                    return Vorschlag(
                        exercise_id, uebung.name, None, naechste.wdh_min,
                        None, letzte_wdh,
                        "steigern",
                        f"{oben} Wiederholungen in allen Sätzen. Der nächste Schritt "
                        f"ist nicht mehr davon, sondern die schwerere Variante: "
                        f"{naechste.name}.",
                        (unten, oben), e1rm, unsicher, plateau,
                    )
                return Vorschlag(
                    exercise_id, uebung.name, self.schritt, unten,
                    None, letzte_wdh,
                    "steigern",
                    f"{oben} Wiederholungen in allen Sätzen. Jetzt Zusatzgewicht: "
                    f"schon {self.schritt:g} kg im Rucksack bringen dich zurück in "
                    f"den Bereich, in dem gewachsen wird.",
                    (unten, oben), e1rm, unsicher, plateau,
                )
            return Vorschlag(
                exercise_id, uebung.name, None, min(oben, (letzte_wdh or unten) + 1),
                None, letzte_wdh,
                "wdh_steigern",
                f"Zuletzt {letzte_wdh}. Eine Wiederholung mehr, bis {oben} in "
                f"allen Sätzen stehen.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        if alle_am_oberen_ende and rir is not None and rir < 1:
            # Am oberen Ende, aber nichts mehr im Tank: das Gewicht zu erhoehen
            # wuerde die naechste Einheit unter den Zielbereich druecken.
            return Vorschlag(
                exercise_id, uebung.name, letztes_gewicht, oben,
                letztes_gewicht, letzte_wdh,
                "wiederholen",
                f"{oben} Wiederholungen, aber nichts mehr im Tank. Dasselbe Gewicht "
                f"noch einmal, diesmal mit ein bis zwei Wiederholungen Reserve.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        if alle_am_oberen_ende:
            neu = runden_auf_schritt((letztes_gewicht or 0) + self.schritt, self.schritt)
            zu_erwarten = self._erwartete_wdh(e1rm, neu)
            return Vorschlag(
                exercise_id, uebung.name, neu, max(unten, zu_erwarten),
                letztes_gewicht, letzte_wdh,
                "steigern",
                f"{oben} Wiederholungen in allen Sätzen erreicht. "
                f"Plus {self.schritt:g} kg, damit landest du wieder bei etwa "
                f"{max(unten, zu_erwarten)} Wiederholungen.",
                (unten, oben), e1rm, unsicher, plateau,
            )

        ziel_wdh = min(oben, (letzte_wdh or unten) + 1)
        zusatz = ""
        if rir is not None and rir >= 3:
            zusatz = (f" Beim letzten Mal waren noch {rir:g} Wiederholungen drin, "
                      f"da geht mehr als eine.")
            ziel_wdh = min(oben, (letzte_wdh or unten) + 2)
        return Vorschlag(
            exercise_id, uebung.name, letztes_gewicht, ziel_wdh,
            letztes_gewicht, letzte_wdh,
            "wdh_steigern",
            f"Gleiches Gewicht, Ziel {ziel_wdh} statt {letzte_wdh} Wiederholungen. "
            f"Ab {oben} in allen Sätzen wird erhöht.{zusatz}",
            (unten, oben), e1rm, unsicher, plateau,
        )

    def _erwartete_wdh(self, e1rm: float | None, gewicht: float) -> int:
        """Wie viele Wiederholungen bei diesem Gewicht zu erwarten sind."""
        if not e1rm or gewicht <= 0 or gewicht >= e1rm:
            return 1
        # Epley nach Wiederholungen aufgeloest.
        return max(1, int(round(30 * (e1rm / gewicht - 1))))

    def _naechste_stufe(self, uebung: Exercise) -> Exercise | None:
        """Die naechstschwerere Uebung derselben Progressionsreihe."""
        if not uebung.reihe:
            return None
        return (
            self.db.query(Exercise)
            .filter(
                Exercise.reihe == uebung.reihe,
                Exercise.stufe > uebung.stufe,
            )
            .order_by(Exercise.stufe)
            .first()
        )

    # -- Aufwaermsaetze ---------------------------------------------------

    def aufwaermen(self, exercise_id: int, arbeitsgewicht: float) -> list[dict]:
        """Aufwaermsaetze zu einem Arbeitsgewicht.

        Uebliche Staffel: 40, 60, 80 Prozent mit absteigenden Wiederholungen.
        Unterhalb von etwa 20 kg Arbeitsgewicht entfaellt das Aufwaermen mit
        Gewicht, weil die Prozentschritte dann kleiner sind als jede
        verfuegbare Scheibe.
        """
        if arbeitsgewicht < 20:
            return []
        staffel = [(0.4, 8), (0.6, 5), (0.8, 3)]
        return [
            {
                "gewicht_kg": runden_auf_schritt(arbeitsgewicht * anteil, self.schritt),
                "wdh": wdh,
                "anteil": anteil,
            }
            for anteil, wdh in staffel
        ]

    # -- Belastung einer Einheit -----------------------------------------

    def einheitslast(self, workout_id: int) -> dict:
        """Kennzahlen einer Einheit: Volumen, Saetze, mittlerer RIR.

        Der mittlere RIR ist die ehrlichste Anstrengungszahl, die ohne
        Messgeraet zu haben ist. Er steht am Ende der Einheit und wandert in
        die Ermuedungsrechnung.
        """
        saetze = (
            self.db.query(WorkoutSet, Exercise)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(WorkoutSet.workout_id == workout_id, *arbeitssatz())
            .all()
        )
        volumen = 0.0
        rir_werte: list[float] = []
        for satz, uebung in saetze:
            if satz.reps:
                volumen += effektive_last(
                    uebung, satz.weight_kg, self.koerpergewicht_kg) * satz.reps
            wert = rir_aus_rpe(satz.rpe)
            if wert is not None:
                rir_werte.append(wert)
        return {
            "volumen_kg": round(volumen, 1),
            "saetze": len(saetze),
            "mittlerer_rir": round(statistics.mean(rir_werte), 1) if rir_werte else None,
            "berechnet_am": datetime.now(timezone.utc),
        }
