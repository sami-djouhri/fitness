"""Nutzerprofil und Ausruestung."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain import DomainError
from app.schemas import (
    GeraetOut, ProfilOut, ProfilUpdate, VorlageOut, AusruestungslueckeOut,
)
from app.services import mealprep_adapter
from app.services.ausruestung import GERAETE, IMMER_VORHANDEN, VORLAGEN
from app.services.empfehlung import EmpfehlungsService
from app.services.profil import ProfilService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profil", tags=["profil"])


def _out(svc: ProfilService) -> ProfilOut:
    profil = svc.holen()
    return ProfilOut(
        geraete=profil.geraete,
        eingerichtet=profil.eingerichtet,
        erfahrung=profil.erfahrung,
        ziel=profil.ziel,
        trainingstage_pro_woche=profil.trainingstage_pro_woche,
        gewichtsschritt_kg=profil.gewichtsschritt_kg,
        kurzhantel_max_kg=profil.kurzhantel_max_kg,
        koerpergewicht_kg=svc.koerpergewicht(),
        koerpergroesse_cm=profil.koerpergroesse_cm,
        geburtsjahr=profil.geburtsjahr,
        geschlecht=profil.geschlecht,
        einschraenkungen=profil.einschraenkungen,
        zielbereich_wdh=list(svc.zielbereich()),
    )


@router.get("", response_model=ProfilOut)
def profil_lesen(db: Session = Depends(get_db)):
    svc = ProfilService(db)
    antwort = _out(svc)
    db.commit()   # legt das Profil beim ersten Zugriff an
    return antwort


def _an_mealprep(
    weight_kg: float | None,
    height_cm: float | None,
    owner_sub: str,
) -> None:
    """Laeuft im Hintergrund-Thread, deshalb eine eigene Ereignisschleife.

    Gleiches Muster und gleiche Begruendung wie in ``routes_body._an_mealprep``:
    das Speichern des Profils darf nicht daran haengen, dass der Nachbardienst
    antwortet, und eine Ausnahme in einer Hintergrundaufgabe reisst in
    Starlette sonst die Antwort mit, die der Nutzer schon bekommen hat.
    """
    try:
        asyncio.run(mealprep_adapter.sync_profil_koerperdaten(
            weight_kg=weight_kg,
            height_cm=height_cm,
            owner_sub=owner_sub,
        ))
    except Exception:
        logger.warning("MealPrep: Abgleich der Profil-Koerperdaten fehlgeschlagen", exc_info=True)


@router.put("", response_model=ProfilOut)
def profil_schreiben(
    body: ProfilUpdate,
    hintergrund: BackgroundTasks,
    db: Session = Depends(get_db),
):
    svc = ProfilService(db)
    daten = body.model_dump(exclude_unset=True)
    svc.aktualisieren(daten)
    antwort = _out(svc)
    db.commit()

    # Gewicht und Groesse teilt MealPrep sich mit uns: es rechnet daraus
    # Grundumsatz und Kalorienziel. Nur die ausdruecklich mitgeschickten Felder
    # werden weitergegeben, damit ein Aufruf, der nur die Geraeteliste aendert,
    # dort nichts anfasst.
    gewicht = daten.get("koerpergewicht_kg")
    groesse = daten.get("koerpergroesse_cm")
    if gewicht is not None or groesse is not None:
        hintergrund.add_task(
            _an_mealprep,
            gewicht,
            groesse,
            db.info.get("owner_sub") or "",
        )
    return antwort


@router.get("/geraete", response_model=list[GeraetOut])
def geraeteliste():
    """Alle Geraete, die man auswaehlen kann.

    Die Selbstverstaendlichkeiten (Boden, Wand, Stuhl) sind nicht dabei: ueber
    die fuehrt niemand Buch, und eine Einrichtung mit dreissig Haken macht
    niemand zu Ende.
    """
    return [
        GeraetOut(
            id=g.id, name=g.name,
            ersatz=list(g.ersatz),
            ersatz_namen=[GERAETE[e].name for e in g.ersatz if e in GERAETE],
            hinweis=g.hinweis,
        )
        for g in GERAETE.values()
        if g.id not in IMMER_VORHANDEN
    ]


@router.get("/vorlagen", response_model=list[VorlageOut])
def vorlagenliste():
    return [
        VorlageOut(
            id=schluessel,
            name=v["name"],
            beschreibung=v["beschreibung"],
            geraete=list(v["geraete"]),
        )
        for schluessel, v in VORLAGEN.items()
    ]


@router.post("/vorlage/{schluessel}", response_model=ProfilOut)
def vorlage_anwenden(schluessel: str, db: Session = Depends(get_db)):
    svc = ProfilService(db)
    try:
        svc.vorlage_anwenden(schluessel)
    except KeyError:
        raise DomainError("Vorlage nicht gefunden", {"vorlage": schluessel})
    antwort = _out(svc)
    db.commit()
    return antwort


@router.get("/luecken", response_model=list[AusruestungslueckeOut])
def ausruestungsluecken(db: Session = Depends(get_db)):
    """Uebungen, die allein an fehlender Ausruestung scheitern.

    Beantwortet die Frage, die sich beim Einrichten stellt: was brachte mir
    ein bestimmtes Geraet? Die Antwort steht sonst nirgends, weil eine
    gefilterte Liste die Ausgeschlossenen nicht zeigt.
    """
    svc = EmpfehlungsService(db)
    return [AusruestungslueckeOut(**e) for e in svc.nicht_machbar()]
