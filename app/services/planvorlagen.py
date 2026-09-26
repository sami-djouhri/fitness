"""Trainingsplaene, die zur vorhandenen Ausruestung passen.

Der Befund: der einzige Plan im Bestand war ein Sechs-Tage-Push/Pull/Legs vom
01.03., zu zwei Dritteln aus Langhantel- und Maschinenuebungen. Wer zu Hause
mit Kurzhanteln und einer Klimmzugstange trainiert, kann davon nichts
gebrauchen, und ein Plan, den man nicht ausfuehren kann, wird nicht
angepasst, sondern ignoriert.

Eine Vorlage beschreibt hier deshalb keine festen Uebungen, sondern
**Bausteine**: "eine Grunduebung fuer die Brust", "eine Zugbewegung
senkrecht". Welche Uebung das wird, entscheidet sich beim Anlegen aus dem,
was der Nutzer hat und auf welcher Progressionsstufe er steht.

★ Deshalb ergibt dieselbe Vorlage im Studio und in der Wohnung einen anderen
Plan, und beide sind ausfuehrbar. Eine Liste fester Uebungsnamen haette
genau das Problem wiederholt, das sie loesen soll.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Exercise, Plan, PlanDay, PlanExercise
from app.services.anteile import gruppenanteile
from app.services.empfehlung import EmpfehlungsService
from app.services.profil import ProfilService


@dataclass
class Baustein:
    """Ein Platz im Trainingstag, beschrieben durch das Ziel statt die Uebung."""

    gruppe: str
    saetze: int = 3
    # Grunduebung bevorzugen. Bei True wird eine mehrgelenkige gesucht und
    # nur ersatzweise eine isolierende genommen.
    grunduebung: bool = False
    # Bewegungsmuster einschraenken, wo es auf die Richtung ankommt: sonst
    # steht in einem Zug-Tag zweimal dieselbe Zugrichtung.
    muster: tuple[str, ...] = ()


@dataclass
class Vorlagentag:
    name: str
    wochentag: int | None
    bausteine: list[Baustein] = field(default_factory=list)


@dataclass
class Planvorlage:
    id: str
    name: str
    beschreibung: str
    tage_pro_woche: int
    tage: list[Vorlagentag]


# Wiederkehrende Bausteine, damit die Vorlagen lesbar bleiben.
def _b(gruppe: str, saetze: int = 3, grund: bool = False,
       *muster: str) -> Baustein:
    return Baustein(gruppe=gruppe, saetze=saetze, grunduebung=grund, muster=muster)


VORLAGEN: dict[str, Planvorlage] = {
    "ganzkoerper_3": Planvorlage(
        id="ganzkoerper_3",
        name="Ganzkörper, 3 Tage",
        beschreibung="Der beste Anfang. Jede Gruppe dreimal die Woche, "
                     "kurze Einheiten, viel Erholung dazwischen.",
        tage_pro_woche=3,
        tage=[
            Vorlagentag("Ganzkörper A", 0, [
                _b("quadrizeps", 3, True, "beugen_knie", "ausfallschritt"),
                _b("brust", 3, True, "druecken_horizontal"),
                _b("latissimus", 3, True, "ziehen_vertikal"),
                _b("seit_delta", 3, False, "seitheben", "druecken_vertikal"),
                _b("bauch", 3),
            ]),
            Vorlagentag("Ganzkörper B", 2, [
                _b("beinbizeps", 3, True, "hueftstreckung"),
                _b("oberer_ruecken", 3, True, "ziehen_horizontal"),
                _b("front_delta", 3, True, "druecken_vertikal"),
                _b("trizeps", 3, False, "armstrecken", "dip"),
                _b("bizeps", 3, False, "armbeugen"),
            ]),
            Vorlagentag("Ganzkörper C", 4, [
                _b("gesaess", 3, True, "hueftstreckung", "ausfallschritt"),
                _b("brust", 3, True, "druecken_schraeg", "druecken_horizontal"),
                _b("latissimus", 3, True, "ziehen_vertikal", "ziehen_horizontal"),
                _b("waden", 3, False, "wade"),
                _b("bauch", 3),
            ]),
        ],
    ),
    "oberkoerper_unterkoerper_4": Planvorlage(
        id="oberkoerper_unterkoerper_4",
        name="Ober und Unter, 4 Tage",
        beschreibung="Zwei Oberkörper-, zwei Beintage. Mehr Volumen je Gruppe "
                     "als beim Ganzkörperplan, ohne dass eine Einheit lang wird.",
        tage_pro_woche=4,
        tage=[
            Vorlagentag("Oberkörper A", 0, [
                _b("brust", 4, True, "druecken_horizontal"),
                _b("latissimus", 4, True, "ziehen_vertikal"),
                _b("front_delta", 3, True, "druecken_vertikal"),
                _b("oberer_ruecken", 3, False, "ziehen_horizontal"),
                _b("trizeps", 3, False, "armstrecken"),
                _b("bizeps", 3, False, "armbeugen"),
            ]),
            Vorlagentag("Unterkörper A", 1, [
                _b("quadrizeps", 4, True, "beugen_knie"),
                _b("beinbizeps", 3, True, "hueftstreckung"),
                _b("gesaess", 3, False, "hueftstreckung", "ausfallschritt"),
                _b("waden", 4, False, "wade"),
                _b("bauch", 3),
            ]),
            Vorlagentag("Oberkörper B", 3, [
                _b("brust", 3, True, "druecken_schraeg"),
                _b("latissimus", 4, True, "ziehen_horizontal"),
                _b("seit_delta", 4, False, "seitheben"),
                _b("hinter_delta", 3, False, "reverse_fly"),
                _b("bizeps", 3, False, "armbeugen"),
                _b("trizeps", 3, False, "armstrecken", "dip"),
            ]),
            Vorlagentag("Unterkörper B", 4, [
                _b("quadrizeps", 4, True, "ausfallschritt", "beugen_knie"),
                _b("beinbizeps", 4, True, "hueftstreckung"),
                _b("adduktoren", 3),
                _b("waden", 4, False, "wade"),
                _b("unterer_ruecken", 2),
            ]),
        ],
    ),
    "push_pull_legs_6": Planvorlage(
        id="push_pull_legs_6",
        name="Push, Pull, Beine, 6 Tage",
        beschreibung="Viel Volumen, jede Gruppe zweimal die Woche. Nur "
                     "sinnvoll, wenn sechs Tage wirklich stattfinden.",
        tage_pro_woche=6,
        tage=[
            Vorlagentag("Push A", 0, [
                _b("brust", 4, True, "druecken_horizontal"),
                _b("front_delta", 3, True, "druecken_vertikal"),
                _b("brust", 3, False, "fliegende", "druecken_schraeg"),
                _b("seit_delta", 4, False, "seitheben"),
                _b("trizeps", 4, False, "armstrecken", "dip"),
            ]),
            Vorlagentag("Pull A", 1, [
                _b("latissimus", 4, True, "ziehen_vertikal"),
                _b("oberer_ruecken", 4, True, "ziehen_horizontal"),
                _b("hinter_delta", 3, False, "reverse_fly"),
                _b("bizeps", 4, False, "armbeugen"),
                _b("unterarm", 3),
            ]),
            Vorlagentag("Beine A", 2, [
                _b("quadrizeps", 4, True, "beugen_knie"),
                _b("beinbizeps", 4, True, "hueftstreckung"),
                _b("gesaess", 3, False, "hueftstreckung"),
                _b("waden", 4, False, "wade"),
                _b("bauch", 3),
            ]),
            Vorlagentag("Push B", 3, [
                _b("front_delta", 4, True, "druecken_vertikal"),
                _b("brust", 4, True, "druecken_schraeg"),
                _b("seit_delta", 4, False, "seitheben"),
                _b("trizeps", 4, False, "armstrecken"),
                _b("brust", 3, False, "fliegende"),
            ]),
            Vorlagentag("Pull B", 4, [
                _b("oberer_ruecken", 4, True, "ziehen_horizontal"),
                _b("latissimus", 4, True, "ziehen_vertikal"),
                _b("trapez", 3, False, "seitheben"),
                _b("bizeps", 4, False, "armbeugen"),
                _b("hinter_delta", 3, False, "reverse_fly"),
            ]),
            Vorlagentag("Beine B", 5, [
                _b("quadrizeps", 4, True, "ausfallschritt"),
                _b("gesaess", 4, True, "hueftstreckung"),
                _b("beinbizeps", 3, False, "hueftstreckung"),
                _b("adduktoren", 3),
                _b("waden", 4, False, "wade"),
            ]),
        ],
    ),
    "kurz_zuhause_3": Planvorlage(
        id="kurz_zuhause_3",
        name="Kurz zu Hause, 3 Tage",
        beschreibung="Je etwa 25 Minuten, ohne Geräte machbar. Für Wochen, in "
                     "denen wenig Zeit ist.",
        tage_pro_woche=3,
        tage=[
            Vorlagentag("Drücken", 0, [
                _b("brust", 4, True, "druecken_horizontal"),
                _b("front_delta", 3, True, "druecken_vertikal"),
                _b("trizeps", 3, False, "dip", "druecken_horizontal"),
            ]),
            Vorlagentag("Ziehen", 2, [
                _b("latissimus", 4, True, "ziehen_vertikal", "ziehen_horizontal"),
                _b("oberer_ruecken", 3, True, "ziehen_horizontal"),
                _b("bizeps", 3, False, "armbeugen", "ziehen_vertikal"),
            ]),
            Vorlagentag("Beine und Rumpf", 4, [
                _b("quadrizeps", 4, True, "beugen_knie", "ausfallschritt"),
                _b("gesaess", 3, True, "hueftstreckung"),
                _b("waden", 3, False, "wade"),
                _b("bauch", 4),
            ]),
        ],
    ),
}


class PlanvorlagenService:
    def __init__(self, db: Session):
        self.db = db
        self.profil = ProfilService(db)
        self.empfehlung = EmpfehlungsService(db)

    def passende_vorlagen(self) -> list[dict]:
        """Alle Vorlagen, mit Hinweis auf die eingestellten Trainingstage."""
        gewuenscht = self.profil.holen().trainingstage_pro_woche
        ergebnis = []
        for v in VORLAGEN.values():
            ergebnis.append({
                "id": v.id,
                "name": v.name,
                "beschreibung": v.beschreibung,
                "tage_pro_woche": v.tage_pro_woche,
                "passt": v.tage_pro_woche == gewuenscht,
            })
        # Die passende zuerst, sonst nach Anzahl der Tage.
        ergebnis.sort(key=lambda v: (not v["passt"], v["tage_pro_woche"]))
        return ergebnis

    def _kandidaten(self) -> list[Exercise]:
        """Uebungen, die dieser Nutzer machen kann, auf seiner Stufe."""
        return self.empfehlung._stufenfilter(
            self.empfehlung.verfuegbare_uebungen())

    def anlegen(self, vorlage_id: str, aktivieren: bool = True) -> Plan:
        vorlage = VORLAGEN.get(vorlage_id)
        if vorlage is None:
            raise KeyError(vorlage_id)

        kandidaten = self._kandidaten()
        anteile = {u.id: gruppenanteile(u) for u in kandidaten}
        profil = self.profil.holen()

        plan = Plan(
            name=vorlage.name,
            description=f"{vorlage.beschreibung} Aus deiner Ausrüstung erzeugt "
                        f"am Tag der Einrichtung, jederzeit änderbar.",
            is_active=False,
        )
        self.db.add(plan)
        self.db.flush()

        for reihenfolge, tag in enumerate(vorlage.tage):
            tagzeile = PlanDay(
                plan_id=plan.id,
                name=tag.name,
                day_of_week=tag.wochentag,
                sort_order=reihenfolge,
            )
            self.db.add(tagzeile)
            self.db.flush()

            # Je Tag keine Uebung zweimal: sonst steht bei knapper Ausruestung
            # dreimal dieselbe Liegestuetze im Plan.
            benutzt: set[int] = set()
            platz = 0
            for baustein in tag.bausteine:
                uebung = self._waehlen(baustein, kandidaten, anteile, benutzt)
                if uebung is None:
                    continue
                benutzt.add(uebung.id)
                unten, oben = self._wiederholungen(uebung, profil.ziel)
                self.db.add(PlanExercise(
                    plan_day_id=tagzeile.id,
                    exercise_id=uebung.id,
                    sort_order=platz,
                    target_sets=baustein.saetze,
                    target_reps_min=unten,
                    target_reps_max=oben,
                    rest_seconds=uebung.pause_s or 90,
                ))
                platz += 1

        if aktivieren:
            for anderer in self.db.query(Plan).filter(Plan.id != plan.id).all():
                anderer.is_active = False
            plan.is_active = True

        return plan

    def _waehlen(self, baustein: Baustein, kandidaten: list[Exercise],
                 anteile: dict[int, dict[str, float]],
                 benutzt: set[int]) -> Exercise | None:
        """Die beste Uebung fuer einen Baustein.

        Reihenfolge der Wuensche, jeder darf entfallen, wenn nichts passt:
        Bewegungsmuster, Grunduebung, hoher Anteil. ★ Ohne dieses
        Nachgeben blieben bei knapper Ausruestung Plaetze leer, und ein Plan
        mit Luecken sieht kaputt aus, obwohl er nur bescheiden ist.
        """
        moegliche = [
            u for u in kandidaten
            if u.id not in benutzt and anteile[u.id].get(baustein.gruppe, 0.0) >= 0.6
        ]
        if not moegliche:
            return None

        def punkte(u: Exercise) -> tuple:
            passt_muster = (not baustein.muster) or (u.muster in baustein.muster)
            passt_art = u.is_compound == baustein.grunduebung
            return (
                0 if passt_muster else 1,
                0 if passt_art else 1,
                -anteile[u.id].get(baustein.gruppe, 0.0),
                u.name,
            )

        return sorted(moegliche, key=punkte)[0]

    def _wiederholungen(self, uebung: Exercise, ziel: str) -> tuple[int, int]:
        """Zielbereich aus dem Ziel des Nutzers, begrenzt vom Katalog.

        ★ Eine Wadenuebung mit 3 bis 6 Wiederholungen ergibt keinen Sinn,
        auch wenn jemand auf Maximalkraft trainiert. Der Katalogbereich ist
        deshalb die Schranke und nicht nur eine Vorbelegung.
        """
        from app.services.profil import ZIELBEREICH
        wunsch_unten, wunsch_oben = ZIELBEREICH.get(ziel, (6, 12))
        unten = max(uebung.wdh_min or 8, wunsch_unten)
        oben = min(uebung.wdh_max or 12, max(unten + 2, wunsch_oben))
        if oben < unten:
            unten, oben = uebung.wdh_min or 8, uebung.wdh_max or 12
        return unten, oben
