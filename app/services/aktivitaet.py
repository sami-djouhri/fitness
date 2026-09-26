"""Aktivitaetsniveau aus dem tatsaechlichen Training ableiten.

★ Die Luecke, die diese Datei schliesst: MealPrep rechnet den Tagesbedarf als
``TDEE = BMR x Aktivitaetsfaktor`` (``app/services/profile.py`` dort). Der
Faktor kommt aus einem Auswahlfeld, das von Hand gesetzt wird und auf
"moderate" vorbelegt ist. Er weiss also nichts davon, ob tatsaechlich
trainiert wurde, obwohl die Fitness-App genau das misst.

Damit war die Kette Training -> Bedarf -> Gerichte -> Einkaufsliste an ihrer
ersten Stelle offen: wer vier Mal pro Woche schwer trainiert, bekam dieselben
Kalorien vorgeschlagen wie jemand, der die App nur eingerichtet hat.

Die Zuordnung unten trifft keine eigene Erfindung, sondern die Stufen, die
MealPrep ohnehin benutzt (Harris-Benedict-Faktoren). Uebersetzt wird nur die
gemessene Haeufigkeit in deren Sprache.

★ Gezaehlt werden nur Trainings mit mindestens einem **abgehakten** Satz. Ein
geplantes, nie absolviertes Training darf den Kalorienbedarf nicht erhoehen,
sonst isst man mehr, weil man vorhatte zu trainieren.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Workout, WorkoutSet
from app.services.satzfilter import arbeitssatz

# Zeitraum der Messung. Vier Wochen daempfen einzelne starke oder schwache
# Wochen, ohne dass eine echte Aenderung ein Vierteljahr braucht.
FENSTER_TAGE = 28

# ★ Ab wie vielen erfassten Trainings die Messung belastbar ist.
#
# Ohne diese Schwelle wuerde die App aus "nichts erfasst" auf "kaum aktiv"
# schliessen und MealPreps Faktor auf 1.2 senken. Das ist falsch und schaedlich
# zugleich: keine Daten heisst nicht kein Training, es heisst nur, dass nichts
# eingetragen wurde. Gemessen am eigenen Bestand: bei null erfassten Saetzen
# haette die Uebertragung den Tagesbedarf von 2259 auf rund 1750 kcal gesenkt,
# bei einem Menschen, der weiter trainiert.
#
# Vier Trainings im Fenster sind eine Woche Erfassung. Darunter wird nichts
# uebertragen, und die Anzeige sagt, warum.
MINDEST_TRAININGS = 4

# Stufen von MealPrep (dort ACTIVITY_MULTIPLIERS) mit dem Faktor, den sie
# bedeuten, und der Haeufigkeit, ab der sie gelten. Obergrenze exklusiv.
STUFEN = [
    ("sedentary", 1.2, 0.5, "kaum Training"),
    ("light", 1.375, 2.5, "1 bis 2 Trainings pro Woche"),
    ("moderate", 1.55, 5.0, "3 bis 4 Trainings pro Woche"),
    ("active", 1.725, 6.5, "5 bis 6 Trainings pro Woche"),
    ("very_active", 1.9, float("inf"), "fast taeglich Training"),
]


@dataclass
class Niveau:
    stufe: str
    faktor: float
    begruendung: str
    trainings_pro_woche: float
    trainings_im_fenster: int
    fenster_tage: int = FENSTER_TAGE
    # Genug erfasst, um daraus einen Kalorienbedarf abzuleiten?
    belastbar: bool = False


def _stufe_fuer(pro_woche: float) -> tuple[str, float, str]:
    for stufe, faktor, obergrenze, text in STUFEN:
        if pro_woche < obergrenze:
            return stufe, faktor, text
    letzte = STUFEN[-1]
    return letzte[0], letzte[1], letzte[3]


def ableiten(db: Session) -> Niveau:
    """Aktivitaetsniveau des Mandanten dieser Session."""
    seit = datetime.now(timezone.utc) - timedelta(days=FENSTER_TAGE)

    # Ein Training zaehlt, wenn es mindestens einen gezaehlten Satz hat.
    # Ueber den Verbund statt ueber die Workout-Tabelle allein: sonst zaehlen
    # leere und rein geplante Sessions mit.
    anzahl = (
        db.query(func.count(func.distinct(Workout.id)))
        .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
        .filter(Workout.started_at >= seit, *arbeitssatz())
        .scalar()
    ) or 0

    pro_woche = round(anzahl / (FENSTER_TAGE / 7), 2)
    stufe, faktor, text = _stufe_fuer(pro_woche)
    belastbar = anzahl >= MINDEST_TRAININGS

    if belastbar:
        begruendung = (
            f"{pro_woche} Trainings pro Woche im Schnitt der letzten "
            f"{FENSTER_TAGE} Tage ({text})"
        )
    else:
        begruendung = (
            f"Erst {anzahl} von {MINDEST_TRAININGS} Trainings erfasst. "
            "Solange wird der Kalorienbedarf nicht aus dem Training abgeleitet."
        )

    return Niveau(
        stufe=stufe,
        faktor=faktor,
        begruendung=begruendung,
        trainings_pro_woche=pro_woche,
        trainings_im_fenster=anzahl,
        belastbar=belastbar,
    )


# --- Uebertragung nach MealPrep ---

# Schluessel im Gedaechtnis (anstoss_merker wird mitbenutzt): haelt fest,
# welche Stufe zuletzt uebertragen wurde. Ohne das schreibt jeder Lauf in ein
# fremdes Profil, auch wenn sich nichts geaendert hat.
MERKER_PRAEFIX = "aktivitaet:"


def uebertragen_faellig(db: Session, niveau: Niveau) -> bool:
    """Stufe geaendert UND belastbar gemessen?

    Ohne die Belastbarkeit wuerde ein frisch eingerichtetes System das Profil
    des Nachbardienstes verschlechtern, statt es zu verbessern.
    """
    from app.models import AnstossMerker

    if not niveau.belastbar:
        return False

    schluessel = MERKER_PRAEFIX + niveau.stufe
    schon = (
        db.query(AnstossMerker)
        .filter(AnstossMerker.schluessel == schluessel)
        .first()
    )
    return schon is None


def uebertragung_vermerken(db: Session, niveau: Niveau) -> None:
    """Neue Stufe vermerken und die alten Stufen-Marken entfernen."""
    from app.models import AnstossMerker

    db.query(AnstossMerker).filter(
        AnstossMerker.schluessel.like(MERKER_PRAEFIX + "%")
    ).delete(synchronize_session=False)
    db.add(AnstossMerker(schluessel=MERKER_PRAEFIX + niveau.stufe))


def an_mealprep(niveau: Niveau, owner_sub: str) -> bool:
    """Stufe an MealPrep schicken. Laeuft im Hintergrund, eigene Schleife.

    ★ Mit eigenem Fangnetz: eine Ausnahme in einer Hintergrundaufgabe reisst
    in Starlette die Antwort mit, die der Nutzer gerade bekommen hat. Die
    eigene Erfassung darf nicht daran haengen, dass der Nachbardienst
    antwortet.
    """
    import asyncio
    import logging

    from app.services import mealprep_adapter

    try:
        return asyncio.run(mealprep_adapter.update_activity_level(
            niveau.stufe, owner_sub=owner_sub,
        ))
    except Exception:
        logging.getLogger(__name__).warning(
            "MealPrep: Aktivitaetsniveau nicht uebertragen", exc_info=True,
        )
        return False
