"""Wochenvolumen, Landmarks und Frische je Muskelgruppe.

Das ist die Rechenschicht, die aus erfassten Saetzen eine Aussage macht.
Vorher gab es zwei Zahlen, die beide etwas anderes meinten und beide
"Volumen" hiessen: ``muscle_freshness`` zaehlte primaere und sekundaere
Muskeln gleich, ``volume_per_muscle`` nur primaere. Dieselbe Woche sah je
nach Ansicht anders aus.

Wie hier gezaehlt wird, und warum so
------------------------------------

**Zwei Zahlen statt einer.** ``direkt`` sind Saetze, in denen der Muskel das
Ziel war (Anteil ab 0.6). ``gewichtet`` zaehlt jede Mitarbeit anteilig mit.
★ Das ist kein Detail: die Landmarks aus der Literatur sind fuer **direkte**
Saetze angegeben, die indirekte Arbeit ist in den Zahlen schon eingepreist.
Wer gewichtete Saetze gegen MEV/MRV haelt, kommt systematisch zu hoch heraus
und bekommt ein Deload vorgeschlagen, das er nicht braucht. Bewertet wird
deshalb ``direkt``, und ``gewichtet`` steht daneben, damit sichtbar bleibt,
wie viel Arbeit ausserhalb der Zielsaetze anfaellt.

**Was als harter Satz zaehlt.** Aufwaermsaetze und ungezaehlte Satzarten
filtert ``satzfilter.arbeitssatz`` schon vorher. Zusaetzlich gilt: ist ein RPE
erfasst und liegt er unter ``RPE_MINDESTENS``, war der Satz weit vom
Muskelversagen entfernt und zaehlt nicht als Wachstumsreiz. Ist kein RPE
erfasst, zaehlt der Satz. ★ Das ist die nachsichtige Richtung, und zwar
absichtlich: die meisten Saetze werden ohne RPE eingetragen, und ein Zaehler,
der die dann alle verwirft, zeigt dauerhaft "zu wenig Volumen" bei jemandem,
der ordentlich trainiert.

**Frische.** Eine Abklingkurve, keine Messung. Jeder Satz hinterlaesst eine
Belastung, die mit der gruppeneigenen Erholungszeit exponentiell abfaellt.
★ Bewusst kein Fitness-Fatigue-Modell nach Banister: dessen Parameter sind
ohne regelmaessige Leistungstests nicht bestimmbar, und ein Modell mit
geratenen Konstanten sieht praeziser aus, als es ist. Was hier steht, ist
eine Faustregel mit sichtbarer Annahme.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Exercise, Workout, WorkoutSet
from app.services.anteile import SCHWELLE_HARTER_SATZ, gruppenanteile, satzvolumen
from app.services.muskulatur import GRUPPEN, MUSKELN, Gruppe
from app.services.satzfilter import arbeitssatz

# Unterhalb dieses RPE war der Satz zu weit vom Versagen entfernt, um als
# Wachstumsreiz zu zaehlen. RPE 6 entspricht rund vier Wiederholungen im Tank.
RPE_MINDESTENS = 6.0

# Wie viele volle Zielsaetze eine Gruppe braucht, um als frisch belastet zu
# gelten. Bezugsgroesse der Frischekurve: eine uebliche Einheit fuer eine
# Gruppe. Steht hier als eine Zahl, damit man sie an einer Stelle aendert.
SAETZE_JE_EINHEIT = 6.0


@dataclass
class Gruppenwoche:
    gruppe: str
    name: str
    region: str
    direkt: float
    gewichtet: float
    volumen_kg: float
    # unter_mv | erhaltung | unter_mev | im_korridor | ueber_mav | ueber_mrv
    bewertung: str
    mv: int
    mev: int
    mav_min: int
    mav_max: int
    mrv: int
    hinweis: str


@dataclass
class Gruppenfrische:
    gruppe: str
    name: str
    region: str
    stunden_seit: float | None
    frische: float          # 0.0 erschoepft bis 1.0 vollstaendig erholt
    bereit_in_stunden: float
    letzte_saetze: float


def _rpe_zaehlt(satz: WorkoutSet) -> bool:
    """Zaehlt der Satz als Reiz? Ohne RPE gilt er als Arbeitssatz."""
    if satz.rpe is None:
        return True
    return float(satz.rpe) >= RPE_MINDESTENS


def _wochenanfang(d: date) -> date:
    return d - timedelta(days=d.weekday())


class VolumenService:
    def __init__(self, db: Session, koerpergewicht_kg: float | None = None):
        self.db = db
        self.koerpergewicht_kg = koerpergewicht_kg

    # ------------------------------------------------------------------
    # Rohdaten
    # ------------------------------------------------------------------

    def _saetze(self, seit: datetime) -> list[tuple[WorkoutSet, Workout, Exercise]]:
        return (
            self.db.query(WorkoutSet, Workout, Exercise)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(*arbeitssatz(), Workout.started_at >= seit)
            .all()
        )

    # ------------------------------------------------------------------
    # Wochenvolumen
    # ------------------------------------------------------------------

    def woche(self, tage: int = 7) -> list[Gruppenwoche]:
        """Volumen der letzten ``tage`` Tage je Gruppe, gegen die Landmarks."""
        seit = datetime.now(timezone.utc) - timedelta(days=tage)
        direkt: dict[str, float] = {}
        gewichtet: dict[str, float] = {}
        volumen: dict[str, float] = {}

        for satz, _workout, uebung in self._saetze(seit):
            if not _rpe_zaehlt(satz):
                continue
            vol = satzvolumen(uebung, satz.weight_kg, satz.reps,
                              self.koerpergewicht_kg)
            for gid, anteil in gruppenanteile(uebung).items():
                gewichtet[gid] = gewichtet.get(gid, 0.0) + anteil
                if anteil >= SCHWELLE_HARTER_SATZ:
                    direkt[gid] = direkt.get(gid, 0.0) + 1.0
                volumen[gid] = volumen.get(gid, 0.0) + vol * anteil

        ergebnis: list[Gruppenwoche] = []
        for gruppe in GRUPPEN.values():
            d = round(direkt.get(gruppe.id, 0.0), 1)
            bewertung, hinweis = self._bewerten(gruppe, d)
            ergebnis.append(Gruppenwoche(
                gruppe=gruppe.id,
                name=gruppe.name,
                region=gruppe.region,
                direkt=d,
                gewichtet=round(gewichtet.get(gruppe.id, 0.0), 1),
                volumen_kg=round(volumen.get(gruppe.id, 0.0), 1),
                bewertung=bewertung,
                mv=gruppe.mv, mev=gruppe.mev,
                mav_min=gruppe.mav_min, mav_max=gruppe.mav_max, mrv=gruppe.mrv,
                hinweis=hinweis,
            ))
        return ergebnis

    def _bewerten(self, gruppe: Gruppe, saetze: float) -> tuple[str, str]:
        """Einordnung in die Landmarks, mit einem Satz Begruendung.

        Die Begruendung steht hier und nicht in der Oberflaeche, weil sie von
        den Zahlen der Gruppe abhaengt. Eine Anzeige, die nur eine Farbe
        zeigt, laesst offen, warum sie diese Farbe zeigt.
        """
        if saetze <= 0:
            if gruppe.mev <= 0:
                # ★ MEV 0 heisst: die Gruppe bekommt genug indirekte Arbeit ab
                # und braucht keine eigene. Ohne diesen Zweig stand hier
                # "0 Sätze wären der Einstieg", was niemand versteht, und die
                # vordere Schulter erschien dauerhaft als Baustelle.
                return "erhaltung", (
                    f"{gruppe.name} braucht keine eigenen Sätze: sie arbeitet bei "
                    f"jedem Drücken mit. Erst ab {gruppe.mav_min} direkten Sätzen "
                    f"lohnt sich gezieltes Training.")
            return "unter_mv", f"Diese Woche noch nichts. {gruppe.mev} Sätze wären der Einstieg."
        # ★ Ein Satz heisst "1 Satz", nicht "1 Sätze". Faellt nur im gerenderten
        # Bild auf, und genau eine Zeile mit falschem Numerus laesst den ganzen
        # Text wie Maschinenausgabe wirken.
        wort = "Satz" if saetze == 1 else "Sätze"
        if saetze < gruppe.mv:
            return "unter_mv", (
                f"{saetze:g} von {gruppe.mv} Sätzen zum Erhalt. "
                f"Darunter geht Substanz verloren.")
        if saetze < gruppe.mev:
            return "erhaltung", (
                f"{saetze:g} {wort} {'hält' if saetze == 1 else 'halten'}, was da ist. "
                f"Ab {gruppe.mev} wächst wieder etwas.")
        if saetze < gruppe.mav_min:
            return "unter_mev", (
                f"{saetze:g} {wort} {'wirkt' if saetze == 1 else 'wirken'}. "
                f"Der beste Bereich beginnt bei {gruppe.mav_min}.")
        if saetze <= gruppe.mav_max:
            return "im_korridor", (
                f"{saetze:g} {wort}, mitten im wirksamen Bereich "
                f"({gruppe.mav_min} bis {gruppe.mav_max}).")
        if saetze <= gruppe.mrv:
            return "ueber_mav", (
                f"{saetze:g} {wort}, oberhalb des besten Bereichs. Bis {gruppe.mrv} "
                f"noch verkraftbar, danach sammelt sich Ermüdung.")
        return "ueber_mrv", (
            f"{saetze:g} {wort}, über der Grenze von {gruppe.mrv}. "
            f"Eine Woche mit weniger Volumen holt den Fortschritt zurück.")

    # ------------------------------------------------------------------
    # Frische
    # ------------------------------------------------------------------

    def frische(self) -> list[Gruppenfrische]:
        """Wie erholt jede Gruppe gerade ist.

        Modell: jeder Zielsatz erzeugt eine Belastungseinheit, die mit der
        Erholungszeit der Gruppe exponentiell abklingt. Nach einer
        Erholungszeit ist rund ein Drittel davon uebrig, nach zweien rund ein
        Achtel. Die Frische ist die Gegenzahl dazu, gedeckelt auf 0 bis 1.

        ★ Das Modell kennt weder Schlaf noch Ernaehrung noch Alter. Es sagt
        ausdruecklich nicht "du bist erholt", sondern "seit der letzten
        Belastung ist so viel Zeit vergangen". Der Unterschied steht in der
        Oberflaeche mit dran.
        """
        jetzt = datetime.now(timezone.utc)
        seit = jetzt - timedelta(days=14)
        belastung: dict[str, float] = {}
        letzter: dict[str, datetime] = {}
        letzte_saetze: dict[str, float] = {}

        for satz, workout, uebung in self._saetze(seit):
            if not _rpe_zaehlt(satz):
                continue
            zeitpunkt = workout.started_at
            if zeitpunkt.tzinfo is None:
                zeitpunkt = zeitpunkt.replace(tzinfo=timezone.utc)
            stunden = max(0.0, (jetzt - zeitpunkt).total_seconds() / 3600.0)

            for gid, anteil in gruppenanteile(uebung).items():
                gruppe = GRUPPEN.get(gid)
                if not gruppe:
                    continue
                abfall = math.exp(-stunden / max(1, gruppe.erholung_stunden))
                belastung[gid] = belastung.get(gid, 0.0) + anteil * abfall
                vorher = letzter.get(gid)
                if vorher is None or zeitpunkt > vorher:
                    letzter[gid] = zeitpunkt
                    letzte_saetze[gid] = anteil
                elif zeitpunkt == vorher:
                    letzte_saetze[gid] = letzte_saetze.get(gid, 0.0) + anteil

        ergebnis: list[Gruppenfrische] = []
        for gruppe in GRUPPEN.values():
            last = belastung.get(gruppe.id, 0.0)
            frisch = max(0.0, min(1.0, math.exp(-last / SAETZE_JE_EINHEIT)))
            zeitpunkt = letzter.get(gruppe.id)
            if zeitpunkt is None:
                stunden_seit = None
            else:
                stunden_seit = round((jetzt - zeitpunkt).total_seconds() / 3600.0, 1)

            # Wann ist die Gruppe wieder bei 90 Prozent? Aus derselben Kurve
            # rueckwaerts gerechnet, damit Anzeige und Modell nicht ausei-
            # nanderlaufen koennen.
            if frisch >= 0.9 or last <= 0:
                bereit_in = 0.0
            else:
                ziel = SAETZE_JE_EINHEIT * -math.log(0.9)
                bereit_in = round(
                    max(0.0, gruppe.erholung_stunden * math.log(last / ziel)), 1)

            ergebnis.append(Gruppenfrische(
                gruppe=gruppe.id,
                name=gruppe.name,
                region=gruppe.region,
                stunden_seit=stunden_seit,
                frische=round(frisch, 3),
                bereit_in_stunden=bereit_in,
                letzte_saetze=round(letzte_saetze.get(gruppe.id, 0.0), 1),
            ))
        return ergebnis

    # ------------------------------------------------------------------
    # Verlauf ueber Wochen
    # ------------------------------------------------------------------

    def verlauf(self, wochen: int = 8) -> list[dict]:
        """Direkte Saetze je Gruppe und Woche. Grundlage der Trendanzeige."""
        seit = datetime.now(timezone.utc) - timedelta(weeks=wochen)
        je_woche: dict[date, dict[str, float]] = {}

        for satz, workout, uebung in self._saetze(seit):
            if not _rpe_zaehlt(satz):
                continue
            tag = workout.started_at
            if isinstance(tag, datetime):
                tag = tag.date()
            woche = _wochenanfang(tag)
            eintrag = je_woche.setdefault(woche, {})
            for gid, anteil in gruppenanteile(uebung).items():
                if anteil >= SCHWELLE_HARTER_SATZ:
                    eintrag[gid] = eintrag.get(gid, 0.0) + 1.0

        return [
            {
                "woche": woche.isoformat(),
                "gruppen": {gid: round(wert, 1) for gid, wert in sorted(werte.items())},
            }
            for woche, werte in sorted(je_woche.items())
        ]

    # ------------------------------------------------------------------
    # Muskelebene, fuer das Koerpermodell
    # ------------------------------------------------------------------

    def je_muskel(self, tage: int = 7) -> dict[str, dict]:
        """Saetze und Volumen bis auf den einzelnen Muskel herunter.

        Das ist die Zahl, die das 3D-Modell einfaerbt. Sie muss auf
        Muskelebene entstehen und nicht auf Gruppenebene: sonst leuchten alle
        vier Quadrizeps-Koepfe gleich, obwohl Beinstrecker und Kniebeuge sie
        unterschiedlich treffen. Genau das war der Befund.
        """
        from app.services.anteile import anteile as muskel_anteile

        seit = datetime.now(timezone.utc) - timedelta(days=tage)
        saetze: dict[str, float] = {}
        volumen: dict[str, float] = {}
        letzter: dict[str, date] = {}

        for satz, workout, uebung in self._saetze(seit):
            if not _rpe_zaehlt(satz):
                continue
            tag = workout.started_at
            if isinstance(tag, datetime):
                tag = tag.date()
            vol = satzvolumen(uebung, satz.weight_kg, satz.reps,
                              self.koerpergewicht_kg)
            for mid, anteil in muskel_anteile(uebung).items():
                saetze[mid] = saetze.get(mid, 0.0) + anteil
                volumen[mid] = volumen.get(mid, 0.0) + vol * anteil
                vorher = letzter.get(mid)
                if vorher is None or tag > vorher:
                    letzter[mid] = tag

        heute = datetime.now(timezone.utc).date()
        return {
            mid: {
                "saetze": round(saetze.get(mid, 0.0), 1),
                "volumen_kg": round(volumen.get(mid, 0.0), 1),
                "tage_seit": (heute - letzter[mid]).days if mid in letzter else None,
            }
            for mid in MUSKELN
        }
