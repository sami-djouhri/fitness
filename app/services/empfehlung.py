"""Was heute dran ist, aus Volumen, Frische und dem, was tatsaechlich da ist.

Loest ``ProgressService.recommendations`` ab. Deren Befund in einem Satz: sie
las den gesamten Katalog und filterte weder nach vorhandener Ausruestung noch
nach der Auswahl des Nutzers. Auf einem Konto mit Kurzhanteln und einer
Klimmzugstange schlug sie Beinpresse, Latzug und Kabelzug-Crossover vor. Die
Vorschlaege waren nicht schlecht begruendet, sie waren nur nicht ausfuehrbar.

Woraus sich die Reihenfolge ergibt
----------------------------------

Jede Muskelgruppe bekommt einen Wert aus vier Teilen. Die Gewichte stehen als
Konstanten oben, damit man sie an einer Stelle sieht und nicht in der Formel
suchen muss.

``bedarf``
    Wie weit die Gruppe diese Woche unter ihrem wirksamen Volumen liegt.
    Der staerkste Teil: eine Gruppe, die diese Woche noch gar nichts hatte,
    steht oben.

``frische``
    Wie erholt sie ist. Eine Gruppe, die gestern hart dran war, gehoert
    heute nicht nach oben, auch wenn sie unter MEV liegt. ★ Ohne diesen Teil
    empfiehlt die App an sieben Tagen hintereinander dasselbe, weil das
    Wochendefizit ja bestehen bleibt.

``ausgleich``
    Abstand zur ausgewogenen Verteilung ueber Druecken, Ziehen und Beine.

``ueberlast``
    Zieht ab, wenn die Gruppe ueber ihrem verkraftbaren Volumen liegt. Dann
    ist mehr davon nachweislich kein Gewinn.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Exercise, ExerciseSelection, Workout, WorkoutSet
from app.services.anteile import gruppenanteile
from app.services.ausruestung import fehlend, mit_ersatz_machbar, machbar, name as geraetename
from app.services.muskulatur import GRUPPEN, IDEALER_PPL_ANTEIL, PPL_JE_GRUPPE
from app.services.profil import ProfilService
from app.services.progression import ProgressionsService
from app.services.satzfilter import arbeitssatz
from app.services.volumen import VolumenService

GEWICHT_BEDARF = 60.0
GEWICHT_FRISCHE = 30.0
GEWICHT_AUSGLEICH = 20.0
ABZUG_UEBERLAST = 50.0

# So viele Uebungen je empfohlener Gruppe.
UEBUNGEN_JE_GRUPPE = 2

# So weit zurueck wird geschaut, um die aktuelle Stufe einer
# Progressionsreihe zu bestimmen. Wer eine Uebung ein halbes Jahr nicht
# gemacht hat, faengt dort nicht dort an, wo er aufgehoert hat.
STUFENFENSTER_TAGE = 60

# Welche Stufe jemand ohne jede Historie bekommt. ★ Nicht die hoechste und
# nicht die niedrigste: die alte Auswahl schlug einem Anfaenger
# Handstand-Liegestuetze vor und daneben die Wandvariante, weil beide
# dieselbe Gruppe treffen und die Stufe niemanden interessierte.
STARTSTUFE: dict[str, int] = {
    "einsteiger": 1,
    "fortgeschritten": 3,
    "erfahren": 4,
}


@dataclass
class Uebungsvorschlag:
    exercise_id: int
    name: str
    kategorie: str
    equipment: str
    gruppe: str
    gruppenname: str
    grunduebung: bool
    anteil: float
    punkte: float
    begruendung: str
    # Was der Progressionsdienst zu dieser Uebung sagt, sofern Historie da ist.
    gewicht_kg: float | None = None
    wdh: int | None = None
    saetze: int = 3
    pause_s: int = 90


@dataclass
class Gruppenempfehlung:
    gruppe: str
    name: str
    region: str
    punkte: float
    bedarf: float
    frische: float
    begruendung: str
    uebungen: list[Uebungsvorschlag]


class EmpfehlungsService:
    def __init__(self, db: Session):
        self.db = db
        self.profil = ProfilService(db)
        self.koerpergewicht = self.profil.koerpergewicht()
        self.volumen = VolumenService(db, self.koerpergewicht)

    # ------------------------------------------------------------------
    # Uebungsbestand des Nutzers
    # ------------------------------------------------------------------

    def verfuegbare_uebungen(self, mit_dehnung: bool = False) -> list[Exercise]:
        """Alle Uebungen, die dieser Nutzer heute tatsaechlich machen kann.

        Drei Filter, in dieser Reihenfolge:

        1. Sichtbar: Katalog plus Eigenes, nichts Fremdes.
        2. Nicht abgewaehlt (``exercise_selection``).
        3. Ausruestung vorhanden.
        """
        bestand = self.profil.geraete()
        sub = self.db.info.get("owner_sub")

        abgewaehlt = {
            z.exercise_id
            for z in self.db.query(ExerciseSelection)
            .filter(ExerciseSelection.is_selected == False)  # noqa: E712
            .all()
        }

        alle = (
            self.db.query(Exercise)
            .execution_options(skip_tenant=True)
            .filter(
                (Exercise.created_by_sub.is_(None)) | (Exercise.created_by_sub == sub)
            )
            .all()
        )
        ergebnis = []
        for uebung in alle:
            if uebung.id in abgewaehlt:
                continue
            if not mit_dehnung and uebung.category in ("Dehnung", "Mobilität"):
                continue
            if not machbar(uebung.benoetigt, bestand):
                continue
            ergebnis.append(uebung)
        return ergebnis

    # ------------------------------------------------------------------
    # Progressionsstufe
    # ------------------------------------------------------------------

    def aktuelle_stufen(self) -> dict[str, int]:
        """Auf welcher Stufe jeder Progressionsreihe dieser Nutzer steht.

        ★★ Ohne diese Auskunft empfiehlt die App innerhalb einer Reihe
        wahllos: gemessen kamen "Liegestütze" und "Liegestütze an der Wand"
        nebeneinander heraus, also Stufe 3 und Stufe 1 derselben Sache, und
        einem Konto ohne jede Historie wurden Handstand-Liegestuetze
        vorgeschlagen. Beides ist kein Ranking-Problem, sondern ein fehlender
        Begriff: eine Reihe hat eine Reihenfolge, und man steht an genau einer
        Stelle darin.

        Bestimmt wird die Stelle aus dem, was zuletzt tatsaechlich gemacht
        wurde. Ohne Historie entscheidet die Erfahrungsstufe aus dem Profil.
        """
        seit = datetime.now(timezone.utc) - timedelta(days=STUFENFENSTER_TAGE)
        zeilen = (
            self.db.query(Exercise.reihe, Exercise.stufe)
            .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.id)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(
                Exercise.reihe.isnot(None),
                Workout.started_at >= seit,
                *arbeitssatz(),
            )
            .all()
        )
        stufen: dict[str, int] = {}
        for reihe, stufe in zeilen:
            if reihe and stufe and stufe > stufen.get(reihe, 0):
                stufen[reihe] = stufe
        return stufen

    def _stufenfilter(self, uebungen: list[Exercise]) -> list[Exercise]:
        """Je Progressionsreihe nur die Uebungen der passenden Stufe.

        Uebungen ohne Reihe (Hanteluebungen, Maschinen) bleiben unberuehrt:
        dort gibt es keine Reihenfolge, und "Seitheben" ist keine Vorstufe
        von irgendetwas.
        """
        stand = self.aktuelle_stufen()
        start = STARTSTUFE.get(self.profil.holen().erfahrung, 2)

        # Welche Stufen es je Reihe ueberhaupt gibt, damit die Zielstufe nicht
        # ueber das Ende hinauszeigt.
        vorhandene: dict[str, set[int]] = {}
        for u in uebungen:
            if u.reihe:
                vorhandene.setdefault(u.reihe, set()).add(u.stufe)

        ziel: dict[str, int] = {}
        for reihe, stufen in vorhandene.items():
            gewuenscht = stand.get(reihe, start)
            # Die naechstniedrigere vorhandene Stufe, falls die gewuenschte
            # fehlt (etwa weil ihr Geraet nicht da ist).
            moegliche = [s for s in sorted(stufen) if s <= gewuenscht]
            ziel[reihe] = moegliche[-1] if moegliche else min(stufen)

        return [u for u in uebungen if not u.reihe or u.stufe == ziel.get(u.reihe)]

    def nicht_machbar(self) -> list[dict]:
        """Uebungen, die nur an fehlender Ausruestung scheitern.

        Fuer die Einrichtungsseite: "mit einer Bank kaemen 14 Uebungen dazu"
        ist eine brauchbare Auskunft, eine wortlos kuerzere Liste nicht.
        """
        bestand = self.profil.geraete()
        sub = self.db.info.get("owner_sub")
        alle = (
            self.db.query(Exercise)
            .execution_options(skip_tenant=True)
            .filter(
                (Exercise.created_by_sub.is_(None)) | (Exercise.created_by_sub == sub)
            )
            .all()
        )
        ergebnis = []
        for uebung in alle:
            luecken = fehlend(uebung.benoetigt, bestand)
            if not luecken:
                continue
            ersetzbar, ersatz = mit_ersatz_machbar(uebung.benoetigt, bestand)
            ergebnis.append({
                "exercise_id": uebung.id,
                "name": uebung.name,
                "fehlt": luecken,
                "fehlt_namen": [geraetename(g) for g in luecken],
                "mit_ersatz": ersetzbar,
                "ersatz_namen": [geraetename(g) for g in ersatz],
            })
        return ergebnis

    # ------------------------------------------------------------------
    # Empfehlung
    # ------------------------------------------------------------------

    def gruppen_nach_bedarf(self) -> list[Gruppenempfehlung]:
        wochen = {w.gruppe: w for w in self.volumen.woche()}
        frischen = {f.gruppe: f for f in self.volumen.frische()}
        faktor = self.profil.landmarkfaktor()

        # Verteilung ueber die Bewegungsrichtungen, fuer den Ausgleichsteil.
        ppl_saetze: dict[str, float] = {}
        for gid, woche in wochen.items():
            richtung = PPL_JE_GRUPPE.get(gid)
            if richtung:
                ppl_saetze[richtung] = ppl_saetze.get(richtung, 0.0) + woche.direkt
        gesamt = sum(ppl_saetze.values()) or 1.0

        bewertet: list[Gruppenempfehlung] = []
        for gruppe in GRUPPEN.values():
            woche = wochen[gruppe.id]
            frische = frischen[gruppe.id]

            ziel = max(1.0, gruppe.mav_min * faktor)
            bedarf = max(0.0, (ziel - woche.direkt) / ziel)

            richtung = PPL_JE_GRUPPE.get(gruppe.id, "core")
            ist_anteil = ppl_saetze.get(richtung, 0.0) / gesamt
            soll_anteil = IDEALER_PPL_ANTEIL.get(richtung, 0.1)
            ausgleich = max(0.0, (soll_anteil - ist_anteil) / soll_anteil)

            punkte = (
                bedarf * GEWICHT_BEDARF
                + frische.frische * GEWICHT_FRISCHE
                + ausgleich * GEWICHT_AUSGLEICH
            )
            if woche.bewertung == "ueber_mrv":
                punkte -= ABZUG_UEBERLAST

            bewertet.append(Gruppenempfehlung(
                gruppe=gruppe.id,
                name=gruppe.name,
                region=gruppe.region,
                punkte=round(punkte, 1),
                bedarf=round(bedarf, 2),
                frische=frische.frische,
                begruendung=self._gruppenbegruendung(woche, frische),
                uebungen=[],
            ))

        bewertet.sort(key=lambda g: g.punkte, reverse=True)
        return bewertet

    def _gruppenbegruendung(self, woche, frische) -> str:
        if frische.frische < 0.5:
            return (f"{woche.name} ist noch belastet, wieder bereit in etwa "
                    f"{frische.bereit_in_stunden:.0f} Stunden.")
        if woche.direkt <= 0:
            return f"{woche.name} war diese Woche noch nicht dran."
        return woche.hinweis

    def empfehlen(self, anzahl_gruppen: int = 3) -> list[Gruppenempfehlung]:
        """Die Gruppen, die heute anstehen, jeweils mit passenden Uebungen."""
        gruppen = self.gruppen_nach_bedarf()
        # ★ Der Stufenfilter gehoert hierher und nicht in
        # ``verfuegbare_uebungen``: dort waeren die uebrigen Stufen auch aus
        # der Uebungsliste und aus dem Plan-Editor verschwunden, und dort
        # will man sie sehen. Gefiltert wird nur, was von selbst vorgeschlagen
        # wird.
        uebungen = self._stufenfilter(self.verfuegbare_uebungen())
        profil = self.profil.holen()
        progression = ProgressionsService(
            self.db, profil.gewichtsschritt_kg, self.koerpergewicht)

        # Anteile einmal vorberechnen, nicht je Gruppe erneut.
        anteile_je_uebung = {u.id: gruppenanteile(u) for u in uebungen}
        vergeben: set[int] = set()
        ergebnis: list[Gruppenempfehlung] = []

        for gruppe in gruppen[:anzahl_gruppen]:
            kandidaten = []
            for uebung in uebungen:
                if uebung.id in vergeben:
                    continue
                anteil = anteile_je_uebung[uebung.id].get(gruppe.gruppe, 0.0)
                if anteil < 0.6:
                    continue
                # Grunduebungen zuerst: mehr Reiz je Satz und je Minute.
                punkte = gruppe.punkte + (10 if uebung.is_compound else 0) + anteil * 5
                kandidaten.append((uebung, anteil, punkte))

            kandidaten.sort(key=lambda k: k[2], reverse=True)
            for uebung, anteil, punkte in kandidaten[:UEBUNGEN_JE_GRUPPE]:
                vergeben.add(uebung.id)
                vorschlag = progression.vorschlag(uebung.id)
                gruppe.uebungen.append(Uebungsvorschlag(
                    exercise_id=uebung.id,
                    name=uebung.name,
                    kategorie=uebung.category,
                    equipment=uebung.equipment,
                    gruppe=gruppe.gruppe,
                    gruppenname=gruppe.name,
                    grunduebung=uebung.is_compound,
                    anteil=anteil,
                    punkte=round(punkte, 1),
                    begruendung=vorschlag.begruendung,
                    gewicht_kg=vorschlag.gewicht_kg,
                    wdh=vorschlag.wdh,
                    saetze=3,
                    pause_s=uebung.pause_s,
                ))
            if gruppe.uebungen:
                ergebnis.append(gruppe)
        return ergebnis

    # ------------------------------------------------------------------
    # Ganze Einheit vorschlagen
    # ------------------------------------------------------------------

    def einheit_vorschlagen(self, dauer_minuten: int = 45) -> dict:
        """Eine vollstaendige Einheit, die in die verfuegbare Zeit passt.

        Rechnung je Uebung: Saetze mal (Arbeitszeit plus Pause). Als Arbeitszeit
        werden 40 Sekunden angesetzt, das ist die Groessenordnung eines Satzes
        mit acht bis zwoelf Wiederholungen im ueblichen Tempo.

        ★ Die Zeit ist der Grund, warum eine Einheit scheitert, nicht die
        Auswahl. Ein Vorschlag mit acht Uebungen fuer eine halbe Stunde wird
        nach der vierten abgebrochen, und was liegen bleibt, ist das Ende der
        Liste, also meistens die kleinen Gruppen.
        """
        sekunden_uebrig = dauer_minuten * 60
        arbeitszeit_je_satz = 40

        gruppen = self.empfehlen(anzahl_gruppen=6)
        ausgewaehlt: list[Uebungsvorschlag] = []
        for gruppe in gruppen:
            for uebung in gruppe.uebungen:
                kosten = uebung.saetze * (arbeitszeit_je_satz + uebung.pause_s)
                if kosten > sekunden_uebrig:
                    continue
                sekunden_uebrig -= kosten
                ausgewaehlt.append(uebung)

        return {
            "dauer_minuten": dauer_minuten,
            "geplante_minuten": round((dauer_minuten * 60 - sekunden_uebrig) / 60),
            "uebungen": ausgewaehlt,
            "gruppen": sorted({u.gruppenname for u in ausgewaehlt}),
        }
