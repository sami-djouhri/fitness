"""Anstoesse: was der Dienst von sich aus melden soll.

Ein Benachrichtigungskanal, nicht mehr. Der Dienst stellt fest, was
meldenswert ist, und gibt es an den optionalen Ausgang (app/mqtt.py). Wohin
es von dort geht, entscheidet die Umgebung: im Haus brain-bus und ntfy, bei
einem Selbsthoster nichts. Ohne eingerichteten Ausgang laeuft alles
unveraendert weiter.

Vorgeschichte: bis 2026-09-12 lag diese Logik in einem Bash-Skript neben dem
Dienst, das ihn per HTTP abfragte, Zustand in zwei Dateien hielt und die
Nutzlast per Zeichenkettenersetzung in Python-Quelltext baute. Ein
Uebungsname mit drei Anfuehrungszeichen fuehrte dort Code aus. Hier ist es
Python mit Datenstrukturen, testbar, und es kennt den Mandanten.

Erweitern heisst: eine Funktion schreiben, die ``Meldung`` zurueckgibt, und
sie in ``REGELN`` eintragen.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AnstossMerker, PersonalRecord
from app.services.progress import ProgressService

logger = logging.getLogger(__name__)

# Ab wie vielen Tagen ohne Training erinnert wird.
PAUSE_TAGE = 3
# Mindestabstand zwischen zwei gleichen Erinnerungen.
ERINNERUNG_ABSTAND = timedelta(hours=20)


@dataclass
class Meldung:
    """Eine Sache, die gemeldet werden soll.

    ``schluessel`` traegt das Gedaechtnis: dieselbe Sache wird nicht zweimal
    gemeldet. ``abstand`` None heisst "nie wiederholen" (ein Rekord ist
    einmalig), sonst die Wartezeit bis zur Wiederholung.
    """

    schluessel: str
    entity: str
    action: str
    nutzlast: dict = field(default_factory=dict)
    abstand: timedelta | None = None


def _erinnerung(db: Session) -> Meldung | None:
    """Seit einer Weile kein Training, und welcher Tag dran ist."""
    fortschritt = ProgressService(db)
    zusammenfassung = fortschritt.dashboard_summary()

    letztes = zusammenfassung.last_workout
    if letztes is None:
        tage = None
    else:
        if letztes.tzinfo is None:
            letztes = letztes.replace(tzinfo=timezone.utc)
        tage = (datetime.now(timezone.utc) - letztes).days
        if tage < PAUSE_TAGE:
            return None

    text = "Noch kein Training erfasst" if tage is None else f"Seit {tage} Tagen kein Training"
    if zusammenfassung.next_plan_day:
        text += f". Dran ist: {zusammenfassung.next_plan_day}"

    return Meldung(
        schluessel="erinnerung",
        entity="training",
        action="erinnerung",
        nutzlast={
            "text": text,
            "tage_ohne_training": tage,
            "naechster_trainingstag": zusammenfassung.next_plan_day,
            "streak": zusammenfassung.current_streak,
        },
        abstand=ERINNERUNG_ABSTAND,
    )


def _rekorde(db: Session) -> list[Meldung]:
    """Neue Bestleistungen der letzten Tage."""
    seit = datetime.now(timezone.utc) - timedelta(days=7)
    zeilen = (
        db.query(PersonalRecord)
        .filter(PersonalRecord.achieved_at >= seit)
        .order_by(PersonalRecord.achieved_at.desc())
        .limit(20)
        .all()
    )
    meldungen = []
    for pr in zeilen:
        name = pr.exercise.name if pr.exercise else ""
        meldungen.append(Meldung(
            # Der Wert steht im Schluessel: ein hoeherer Rekord an derselben
            # Uebung ist eine neue Meldung, derselbe nicht.
            schluessel=f"rekord:{pr.exercise_id}:{pr.pr_type}:{pr.value}",
            entity="rekord",
            action="erreicht",
            nutzlast={"uebung": name, "art": pr.pr_type, "wert": pr.value},
        ))
    return meldungen


# Reihenfolge = Reihenfolge der Meldungen. Eine Regel gibt None, eine Meldung
# oder eine Liste zurueck.
REGELN = [_erinnerung, _rekorde]


def _schon_gemeldet(db: Session, meldung: Meldung) -> bool:
    """Gedaechtnis je Mandant. Das Scoping macht app/tenant.py."""
    merker = (
        db.query(AnstossMerker)
        .filter(AnstossMerker.schluessel == meldung.schluessel)
        .first()
    )
    if merker is None:
        return False
    if meldung.abstand is None:
        return True
    gemeldet = merker.gemeldet_am
    if gemeldet.tzinfo is None:
        gemeldet = gemeldet.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - gemeldet < meldung.abstand


def _merken(db: Session, meldung: Meldung) -> None:
    merker = (
        db.query(AnstossMerker)
        .filter(AnstossMerker.schluessel == meldung.schluessel)
        .first()
    )
    jetzt = datetime.now(timezone.utc)
    if merker is None:
        db.add(AnstossMerker(schluessel=meldung.schluessel, gemeldet_am=jetzt))
    else:
        merker.gemeldet_am = jetzt


def faellige_meldungen(db: Session) -> list[Meldung]:
    """Was fuer den Mandanten dieser Session zu melden ist."""
    faellig: list[Meldung] = []
    for regel in REGELN:
        ergebnis = regel(db)
        if ergebnis is None:
            continue
        for meldung in (ergebnis if isinstance(ergebnis, list) else [ergebnis]):
            if not _schon_gemeldet(db, meldung):
                faellig.append(meldung)
    return faellig


def melden(db: Session, owner_sub: str, trockenlauf: bool = False) -> list[dict]:
    """Faellige Meldungen senden und im Gedaechtnis vermerken.

    Vermerkt wird nur, was den Ausgang wirklich erreicht hat. Ein nicht
    erreichbarer Broker darf die Meldung nicht verschlucken: sonst waere der
    erste echte Anlass genau der, der verloren geht.
    """
    from app.mqtt import publisher

    ergebnis = []
    for meldung in faellige_meldungen(db):
        nutzlast = {"quelle": "fitness", "owner_sub": owner_sub, **meldung.nutzlast}
        if trockenlauf:
            ergebnis.append({"schluessel": meldung.schluessel, "gesendet": False,
                             "nutzlast": nutzlast})
            continue
        gesendet = publisher.publish(meldung.entity, meldung.action, nutzlast)
        if gesendet:
            _merken(db, meldung)
        ergebnis.append({"schluessel": meldung.schluessel, "gesendet": gesendet,
                         "nutzlast": nutzlast})
    return ergebnis


def alle_pruefen(trockenlauf: bool = False) -> dict:
    """Alle Mandanten pruefen und Faelliges melden.

    Gemeinsamer Weg fuer den Endpunkt und den Lauf im Container
    (``app/anstoss_lauf.py``), damit beide dasselbe tun.
    """
    from app.mandant_ableiten import alle_mandanten
    from app.mqtt import publisher

    mandanten = alle_mandanten()
    ergebnis = {"mandanten": len(mandanten), "meldungen": [], "kanal": publisher.zustand()}

    for sub in mandanten:
        # Eigene Session je Mandant: das Scoping in app/tenant.py liest den
        # Mandanten aus session.info, nicht aus dem Aufruf.
        db = SessionLocal()
        db.info["owner_sub"] = sub
        try:
            meldungen = melden(db, sub, trockenlauf=trockenlauf)
            if not trockenlauf:
                db.commit()
            for m in meldungen:
                ergebnis["meldungen"].append({"owner_sub": sub, **m})
        except Exception:
            db.rollback()
            # Ein Mandant mit kaputten Daten darf die uebrigen nicht aufhalten.
            logger.warning("Anstoss fuer einen Mandanten fehlgeschlagen", exc_info=True)
        finally:
            db.close()

    ergebnis["kanal"] = publisher.zustand()
    return ergebnis
