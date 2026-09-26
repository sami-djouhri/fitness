"""Was trainiere ich JETZT.

Owner-Entscheid 2026-09-14, in einem Satz: **der Kalender plant, wann Zeit für
Training ist, diese App hält bereit, was in genau diese Zeit gehört.** Die
Arbeitsteilung ist keine Geschmacksfrage, sondern löst einen Widerspruch auf.
Vorher sagten beide Seiten etwas über den Termin: der Plan trug feste Wochentage
("Montag ist Drücken"), der Kalender rechnete unabhängig davon einen Trainings-
block, und wer beides nebeneinander las, bekam zwei Antworten auf dieselbe Frage.

Drei Dinge fließen zusammen, und keines davon ist verhandelbar:

``Zeit``
    Wie viele Minuten wirklich da sind. Kommt aus dem Trainingsblock der
    Tagesdecke, weil nur der Kalender den ganzen Tag kennt. ★ Ohne diese Zahl
    ist jeder Vorschlag geraten: eine Einheit für 90 Minuten in einem Fenster
    von 40 wird nach der Hälfte abgebrochen, und liegen bleibt regelmäßig das
    Ende der Liste, also die kleinen Gruppen.

``Plan``
    Was nach der eigenen Aufteilung dran ist. Wer sich einen Push/Pull/Legs-Plan
    gegeben hat, will Push hören und nicht, was ein Volumenrechner für optimal
    hält. Der Plan schlägt die Rechnung, solange es einen gibt.

``Erholung``
    Was der Körper heute tragen kann. Sie kürzt und begründet, ersetzt aber den
    Plan nicht: eine Gruppe, die noch belastet ist, rutscht nach hinten oder
    fällt weg, und das wird gesagt.

★★ Was hier **nicht** passiert: ein Zeitpunkt vorschlagen. Es gibt keine Zeile,
die "trainiere heute Abend um 18 Uhr" sagt. Fragt jemand nach Training ohne
verfügbare Minuten, antwortet der Dienst mit einer ausgewiesenen Vorgabe und
sagt dazu, dass sie geraten ist (``minuten_quelle``). Eine erfundene Zahl, die
wie eine gemessene aussieht, ist der Fehler, den diese Trennung verhindern soll.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import Plan, PlanDay
from app.services import kalender_adapter
from app.services.ausruestung import machbar
from app.services.empfehlung import EmpfehlungsService, Uebungsvorschlag
from app.services.profil import ProfilService
from app.services.progression import ProgressionsService

#: Womit gerechnet wird, wenn niemand eine Dauer nennt. Bewusst eine runde,
#: mittlere Zahl: sie ist erkennbar eine Vorgabe und keine Messung, und sie wird
#: als solche ausgewiesen.
VORGABE_MINUTEN = 45

#: Unter dieser Dauer lohnt der Aufbau nicht mehr. Der Dienst verweigert nichts,
#: er sagt es nur dazu: wer zwölf Minuten hat, bekommt zwei Übungen und den
#: Hinweis, dass das eine Ergänzung ist und keine Einheit.
KURZ_MINUTEN = 20

#: Arbeitszeit je Satz in Sekunden, dieselbe Annahme wie in
#: ``empfehlung.einheit_vorschlagen``: acht bis zwölf Wiederholungen im üblichen
#: Tempo. Steht hier erneut, weil die Plan-Strecke ihre eigene Rechnung braucht.
ARBEITSZEIT_JE_SATZ = 40


@dataclass
class JetztUebung:
    """Eine Übung, wie sie jetzt ausgeführt werden soll."""

    exercise_id: int
    name: str
    kategorie: str
    equipment: str
    gruppenname: str
    saetze: int
    pause_s: int
    wdh: int | None = None
    gewicht_kg: float | None = None
    begruendung: str = ""
    #: Wurde sie aus Zeitgründen gekürzt? Dann steht hier, von wie vielen Sätzen.
    gekuerzt_von: int | None = None
    #: Nicht aus dem Plan, sondern zum Auffüllen des Fensters dazugenommen.
    ergaenzt: bool = False


@dataclass
class TrainingJetzt:
    minuten: int
    #: ``kalender`` (aus dem Trainingsblock), ``angefragt`` (Aufrufer nannte sie)
    #: oder ``vorgabe`` (niemand wusste es). Die Unterscheidung gehört in die
    #: Antwort: eine Vorgabe darf nicht wie eine Messung aussehen.
    minuten_quelle: str
    quelle: str  #: ``plan`` oder ``bedarf``
    titel: str
    begruendung: str
    geplante_minuten: int
    uebungen: list[JetztUebung] = field(default_factory=list)
    gruppen: list[str] = field(default_factory=list)
    plantag: str | None = None
    plantag_id: int | None = None
    hinweise: list[str] = field(default_factory=list)


class JetztService:
    def __init__(self, db: Session):
        self.db = db
        self.empfehlung = EmpfehlungsService(db)
        self.profil = ProfilService(db)
        self._kalender = kalender_adapter.KalenderAdapter()

    # ------------------------------------------------------------------
    # Der aktive Plantag
    # ------------------------------------------------------------------

    def _aktiver_plantag(self) -> PlanDay | None:
        """Welcher Tag des aktiven Plans als nächstes dran ist.

        ★ Bewusst **ohne** Wochentagsbindung. Ein Plan, der "Montag ist
        Drücken" sagt, trifft eine Aussage über den Kalender, und genau die
        gehört seit dem Owner-Entscheid dorthin. Gerechnet wird deshalb nur die
        Rotation: der Tag nach dem, der zuletzt trainiert wurde. Sie kommt ohne
        Kalender aus und geht nicht kaputt, wenn eine Woche ausfällt.
        """
        plan = self.db.query(Plan).filter(Plan.is_active == True).first()  # noqa: E712
        if not plan:
            return None
        tage = sorted(plan.days, key=lambda d: (d.sort_order, d.id))
        if not tage:
            return None

        from app.models import Workout

        tag_ids = [t.id for t in tage]
        letztes = (
            self.db.query(Workout)
            .filter(Workout.plan_day_id.in_(tag_ids))
            .order_by(Workout.started_at.desc())
            .first()
        )
        if not letztes:
            return tage[0]
        stelle = next(
            (i for i, t in enumerate(tage) if t.id == letztes.plan_day_id), None
        )
        if stelle is None:
            return tage[0]
        return tage[(stelle + 1) % len(tage)]

    # ------------------------------------------------------------------
    # Plan-Strecke
    # ------------------------------------------------------------------

    def _aus_plan(self, tag: PlanDay, minuten: int) -> tuple[list[JetztUebung], list[str]]:
        """Die Übungen eines Plantags, zugeschnitten auf die verfügbare Zeit.

        ★ Gekürzt wird an den **Sätzen**, nicht an den Übungen. Wer eine
        Push-Einheit auf 30 Minuten kürzt, indem er die letzten drei Übungen
        streicht, trainiert Brust dreifach und Trizeps gar nicht. Weniger Sätze
        über alle Übungen hinweg hält die Aufteilung, um die es beim Plan geht.
        Erst wenn auch ein einzelner Satz je Übung nicht mehr passt, fallen
        Übungen weg, und zwar von hinten.
        """
        bestand = self.profil.geraete()
        progression = ProgressionsService(
            self.db,
            self.profil.holen().gewichtsschritt_kg,
            self.empfehlung.koerpergewicht,
        )
        frischen = {f.gruppe: f for f in self.empfehlung.volumen.frische()}
        from app.services.anteile import gruppenanteile

        hinweise: list[str] = []
        roh: list[JetztUebung] = []
        for platz in tag.exercises:
            uebung = platz.exercise
            if uebung is None:
                continue
            # Ausrüstung kann sich geändert haben, seit der Plan entstand.
            if not machbar(uebung.benoetigt, bestand):
                hinweise.append(
                    f"{uebung.name} steht im Plan, die Ausrüstung dafür fehlt gerade."
                )
                continue
            vorschlag = progression.vorschlag(uebung.id)
            anteile = gruppenanteile(uebung)
            haupt = max(anteile, key=anteile.get) if anteile else None
            frische = frischen.get(haupt) if haupt else None
            roh.append(JetztUebung(
                exercise_id=uebung.id,
                name=uebung.name,
                kategorie=uebung.category,
                equipment=uebung.equipment,
                # ★ Rueckfall auf die Kategorie. Eine selbst angelegte Uebung
                # hat keine hinterlegten Muskelanteile, und ohne den Rueckfall
                # steht in der Ansicht eine leere Klammer statt "Brust".
                gruppenname=_gruppenname(haupt) if haupt else uebung.category,
                saetze=platz.target_sets,
                pause_s=platz.rest_seconds,
                wdh=vorschlag.wdh,
                gewicht_kg=vorschlag.gewicht_kg,
                begruendung=vorschlag.begruendung,
            ))
            if frische is not None and frische.frische < 0.5:
                hinweise.append(
                    f"{_gruppenname(haupt)} ist noch belastet, wieder bereit in etwa "
                    f"{frische.bereit_in_stunden:.0f} Stunden."
                )

        gekuerzt = _auf_zeit_kuerzen(roh, minuten)
        if len(gekuerzt) < len(roh):
            weggefallen = len(roh) - len(gekuerzt)
            hinweise.append(
                f"{weggefallen} Übung{'en' if weggefallen > 1 else ''} passen nicht "
                f"in {minuten} Minuten und sind weggelassen."
            )

        ergaenzt, fuell_hinweise = self._auffuellen(gekuerzt, minuten)
        hinweise.extend(fuell_hinweise)
        return ergaenzt, hinweise

    def _auffuellen(
        self, uebungen: list[JetztUebung], minuten: int
    ) -> tuple[list[JetztUebung], list[str]]:
        """Übrige Zeit des Fensters mit dem füllen, was sonst zu kurz kommt.

        ★★ Ohne diesen Schritt ist die ganze Trennung halb: der Kalender
        reserviert 60 Minuten, ein Plantag mit vier Übungen füllt 26, und 34
        Minuten reservierte Zeit verfallen wortlos. Gemessen am 2026-09-16 an
        einem gewöhnlichen Push/Pull/Legs-Plan. Die elf grünen Tests sahen es
        nicht, weil alle nur prüften, dass die Einheit nicht **überläuft**.

        Ergänzt wird nach Bedarf und Erholung, also mit Gruppen, die diese
        Woche zu kurz kamen, und nie mit etwas, das schon im Plan steht. Mehr
        Sätze derselben vier Übungen wären der schlechtere Tausch: eine
        zusätzliche Gruppe bringt mehr als der fünfte Satz auf derselben.
        """
        rest = minuten * 60 - sum(
            u.saetze * (ARBEITSZEIT_JE_SATZ + u.pause_s) for u in uebungen
        )
        # Unter einer Übung Platz lohnt das Ergänzen nicht: drei Sätze mit
        # neunzig Sekunden Pause brauchen rund sechseinhalb Minuten.
        if rest < 6 * 60:
            return uebungen, []

        schon_da = {u.exercise_id for u in uebungen}
        # ★★ Je Gruppe höchstens eine Ergänzung, und nie mehr Ergänzungen als
        # der Plantag selbst Übungen hat. Beide Grenzen stammen aus dem, was
        # die Klartext-Probe am 2026-09-16 zeigte: ohne sie standen in einem
        # Fenster von 60 Minuten **eine** Planübung und **sieben** Zugaben, und
        # das Ergebnis hieß weiterhin "Drücken". Die erste Grenze fing dabei
        # zusätzlich drei Varianten derselben Übung ab (Liegestütze, an der
        # Wand, plyometrisch), die alle als Brust geführt werden.
        gruppen_da = {u.gruppenname for u in uebungen if u.gruppenname}
        deckel = max(2, len(uebungen))
        zusatz: list[JetztUebung] = []
        for gruppe in self.empfehlung.empfehlen(anzahl_gruppen=6):
            for vorschlag in gruppe.uebungen:
                if len(zusatz) >= deckel:
                    break
                if vorschlag.exercise_id in schon_da:
                    continue
                if vorschlag.gruppenname and vorschlag.gruppenname in gruppen_da:
                    continue
                kosten = vorschlag.saetze * (ARBEITSZEIT_JE_SATZ + vorschlag.pause_s)
                if kosten > rest:
                    continue
                rest -= kosten
                schon_da.add(vorschlag.exercise_id)
                if vorschlag.gruppenname:
                    gruppen_da.add(vorschlag.gruppenname)
                eintrag = _aus_vorschlag(vorschlag)
                eintrag.ergaenzt = True
                zusatz.append(eintrag)

        if not zusatz:
            return uebungen, [
                f"Im Fenster von {minuten} Minuten bleibt Zeit übrig, es passt "
                "aber nichts Sinnvolles mehr dazu."
            ]
        # Ohne `sorted(set(...))` stand hier "Brust, Brust, Trizeps, Trizeps".
        gruppen = sorted({u.gruppenname for u in zusatz if u.gruppenname})
        namen = ", ".join(gruppen)
        kam = "kam" if len(gruppen) == 1 else "kamen"
        return uebungen + zusatz, [
            f"{len(zusatz)} Übung{'en' if len(zusatz) > 1 else ''} ergänzt, weil das "
            f"Fenster länger ist als der Plantag"
            + (f" ({namen} {kam} diese Woche zu kurz)." if namen else ".")
        ]

    # ------------------------------------------------------------------
    # Die Auskunft
    # ------------------------------------------------------------------

    def training(
        self,
        minuten: int | None = None,
        minuten_quelle: str = "angefragt",
        heute: date | None = None,
    ) -> TrainingJetzt:
        """Was jetzt trainiert wird, in der Zeit, die da ist.

        ``minuten`` ist die verfügbare Zeit, üblicherweise aus dem
        Trainingsblock der Tagesdecke. Fehlt sie, wird mit ``VORGABE_MINUTEN``
        gerechnet und das in ``minuten_quelle`` ausgewiesen.
        """
        if minuten is None or minuten <= 0:
            minuten = VORGABE_MINUTEN
            minuten_quelle = "vorgabe"

        hinweise: list[str] = []
        if minuten < KURZ_MINUTEN:
            hinweise.append(
                f"{minuten} Minuten sind eine Ergänzung, keine ganze Einheit."
            )

        tag = self._aktiver_plantag()
        if tag is not None and tag.exercises:
            uebungen, plan_hinweise = self._aus_plan(tag, minuten)
            hinweise.extend(plan_hinweise)
            if uebungen:
                ergebnis = TrainingJetzt(
                    minuten=minuten,
                    minuten_quelle=minuten_quelle,
                    quelle="plan",
                    titel=tag.name,
                    begruendung=(
                        f"Nach deiner Aufteilung ist '{tag.name}' als nächstes dran."
                    ),
                    geplante_minuten=_dauer_minuten(uebungen),
                    uebungen=uebungen,
                    gruppen=sorted({u.gruppenname for u in uebungen if u.gruppenname}),
                    plantag=tag.name,
                    plantag_id=tag.id,
                    hinweise=hinweise,
                )
                self._tagestyp_ergaenzen(ergebnis, heute)
                return ergebnis
            # Kein einziger Platz ausführbar: weiter zur Bedarfs-Strecke, statt
            # eine leere Einheit zu melden.
            hinweise.append(
                f"Aus '{tag.name}' ist heute nichts ausführbar, deshalb nach Bedarf."
            )

        vorschlag = self.empfehlung.einheit_vorschlagen(dauer_minuten=minuten)
        uebungen = [_aus_vorschlag(u) for u in vorschlag["uebungen"]]
        ergebnis = TrainingJetzt(
            minuten=minuten,
            minuten_quelle=minuten_quelle,
            quelle="bedarf",
            titel="Freies Training",
            begruendung=(
                "Kein aktiver Plan, deshalb nach Bedarf und Erholung zusammengestellt."
                if tag is None
                else "Nach Bedarf und Erholung zusammengestellt."
            ),
            geplante_minuten=vorschlag["geplante_minuten"],
            uebungen=uebungen,
            gruppen=vorschlag["gruppen"],
            hinweise=hinweise,
        )
        self._tagestyp_ergaenzen(ergebnis, heute)
        return ergebnis

    def _tagestyp_ergaenzen(self, ergebnis: TrainingJetzt, heute: date | None) -> None:
        """Den Tagestyp als Hinweis anhängen, nie als Austausch.

        ⚠️ Der Vorschlag wird an einem Feiertag **nicht** umgebaut. Die App sagt
        nur dazu, dass heute nichts sein muss. Eine Anwendung, die den Inhalt
        hinter dem Rücken des Nutzers tauscht, ist schwerer zu durchschauen als
        eine, die eine Zeile mehr schreibt.
        """
        tag = heute or datetime.now(timezone.utc).date()
        tagestyp = self._kalender.tagestyp(tag)
        hinweis = kalender_adapter.hinweis(tagestyp, ergebnis.plantag or ergebnis.titel)
        if hinweis:
            ergebnis.hinweise.append(hinweis)


# ----------------------------------------------------------------------
# Hilfen
# ----------------------------------------------------------------------


def _gruppenname(gruppe_id: str) -> str:
    from app.services.muskulatur import GRUPPEN

    gruppe = GRUPPEN.get(gruppe_id)
    return gruppe.name if gruppe else gruppe_id


def _dauer_minuten(uebungen: list[JetztUebung]) -> int:
    sekunden = sum(u.saetze * (ARBEITSZEIT_JE_SATZ + u.pause_s) for u in uebungen)
    return round(sekunden / 60)


def _auf_zeit_kuerzen(uebungen: list[JetztUebung], minuten: int) -> list[JetztUebung]:
    """Sätze reduzieren, bis die Einheit in die Zeit passt.

    Erst gleichmäßig über alle Übungen (von hinten, damit die erste Übung ihre
    Sätze am längsten behält), dann fallen Übungen von hinten weg. Ein Satz je
    Übung ist die Untergrenze: darunter ist es keine Übung mehr, sondern eine
    Aufwärmbewegung.
    """
    if not uebungen:
        return []
    budget = minuten * 60
    arbeit = [
        JetztUebung(**{**u.__dict__}) for u in uebungen
    ]

    def kosten() -> int:
        return sum(u.saetze * (ARBEITSZEIT_JE_SATZ + u.pause_s) for u in arbeit)

    # Stufe 1: Sätze abbauen, solange irgendwo mehr als einer steht.
    while kosten() > budget and any(u.saetze > 1 for u in arbeit):
        for u in reversed(arbeit):
            if u.saetze > 1:
                if u.gekuerzt_von is None:
                    u.gekuerzt_von = u.saetze
                u.saetze -= 1
                break

    # Stufe 2: Übungen von hinten streichen.
    while arbeit and kosten() > budget:
        arbeit.pop()

    return arbeit


def _aus_vorschlag(u: Uebungsvorschlag) -> JetztUebung:
    return JetztUebung(
        exercise_id=u.exercise_id,
        name=u.name,
        kategorie=u.kategorie,
        equipment=u.equipment,
        gruppenname=u.gruppenname,
        saetze=u.saetze,
        pause_s=u.pause_s,
        wdh=u.wdh,
        gewicht_kg=u.gewicht_kg,
        begruendung=u.begruendung,
    )
