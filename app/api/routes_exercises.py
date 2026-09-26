"""Exercise catalog routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Exercise
from app.schemas import (
    ExerciseCreate, ExerciseOut, ExerciseSelectUpdate, ExerciseUpdate,
    ProgressionsvorschlagOut,
)
from app.services.ausruestung import fehlend, machbar as _machbar, name as geraetename
from app.services.exercises import ExerciseService
from app.services.profil import ProfilService
from app.services.progression import ProgressionsService

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


def _out(e: Exercise, auswahl: dict[int, bool] | None = None,
         bestand: frozenset[str] | None = None) -> ExerciseOut:
    # ``is_selected`` stammt aus der Auswahl des Mandanten, nicht mehr aus der
    # Spalte am geteilten Katalog. Kein Eintrag bedeutet ausgewaehlt.
    luecken = fehlend(e.benoetigt, bestand) if bestand is not None else []
    return ExerciseOut(
        id=e.id,
        name=e.name,
        category=e.category,
        equipment=e.equipment,
        primary_muscles=e.primary_muscles,
        secondary_muscles=e.secondary_muscles,
        is_compound=e.is_compound,
        is_selected=(auswahl or {}).get(e.id, True),
        notes=e.notes,
        is_eigene=e.created_by_sub is not None,
        muskel_anteile=e.muskel_anteile,
        benoetigt=e.benoetigt,
        muster=e.muster,
        kg_anteil=e.kg_anteil or 0.0,
        griff=e.griff,
        reihe=e.reihe,
        stufe=e.stufe or 0,
        einseitig=bool(e.einseitig),
        ist_zeit=bool(e.ist_zeit),
        wdh_min=e.wdh_min or 8,
        wdh_max=e.wdh_max or 12,
        pause_s=e.pause_s or 90,
        ausfuehrung=e.ausfuehrung,
        fehler=e.fehler,
        machbar=not luecken,
        fehlt_namen=[geraetename(g) for g in luecken],
    )


def _liste_out(svc: ExerciseService, uebungen: list[Exercise],
               bestand: frozenset[str] | None) -> list[ExerciseOut]:
    auswahl = svc.auswahl([e.id for e in uebungen])
    return [_out(e, auswahl, bestand) for e in uebungen]


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    category: str | None = None,
    equipment: str | None = None,
    search: str | None = None,
    region: str | None = None,
    muscle: str | None = None,
    gruppe: str | None = None,
    muster: str | None = None,
    # ★ Standardmaessig AUS, damit bestehende Aufrufer dieselbe Liste bekommen
    # wie bisher. Wer nur Machbares will, sagt es. Die Alternative waere
    # gewesen, still zu filtern, und dann fehlen Uebungen ohne sichtbaren Grund.
    nur_machbar: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    svc = ExerciseService(db)
    bestand = ProfilService(db).geraete()

    if muscle:
        # Feinauswahl: eine einzelne Muskelkennung (``vastus_medialis``) oder
        # der alte Freitextname ("Quadrizeps"). Beides muss gehen, weil das
        # Koerpermodell Kennungen schickt und aeltere Clients Namen.
        ergebnis = svc.nach_muskel(muscle, category=category)
    elif gruppe:
        ergebnis = svc.nach_gruppe(gruppe, category=category)
    elif region:
        ergebnis = svc.list_by_region(region, category=category)
    else:
        ergebnis = svc.list_all(category=category, equipment=equipment,
                                search=search, muster=muster,
                                skip=0, limit=limit + skip)

    if nur_machbar:
        ergebnis = [e for e in ergebnis if _machbar(e.benoetigt, bestand)]

    return _liste_out(svc, ergebnis[skip:skip + limit], bestand)


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    svc = ExerciseService(db)
    ex = svc.get(exercise_id)
    return _out(ex, svc.auswahl([ex.id]), ProfilService(db).geraete())


@router.get("/{exercise_id}/progression", response_model=ProgressionsvorschlagOut)
def progression(exercise_id: int, db: Session = Depends(get_db)):
    """Was beim naechsten Mal dran ist, mit Begruendung.

    Loest ``/workouts/overload-suggestion`` ab: die kannte zwei Faelle und
    verglich jede Uebung mit einer fest eingebauten Zwoelf, unabhaengig von
    ihrem Zielbereich.
    """
    profil = ProfilService(db)
    einstellungen = profil.holen()
    svc = ProgressionsService(db, einstellungen.gewichtsschritt_kg,
                              profil.koerpergewicht())
    v = svc.vorschlag(exercise_id)
    aufwaermen = svc.aufwaermen(exercise_id, v.gewicht_kg) if v.gewicht_kg else []
    db.commit()
    return ProgressionsvorschlagOut(
        exercise_id=v.exercise_id,
        exercise_name=v.exercise_name,
        gewicht_kg=v.gewicht_kg,
        wdh=v.wdh,
        letztes_gewicht_kg=v.letztes_gewicht_kg,
        letzte_wdh=v.letzte_wdh,
        art=v.art,
        begruendung=v.begruendung,
        zielbereich=list(v.zielbereich),
        e1rm=v.e1rm,
        e1rm_unsicher=v.e1rm_unsicher,
        plateau_seit=v.plateau_seit,
        aufwaermsaetze=aufwaermen,
    )


@router.post("", response_model=ExerciseOut, status_code=201)
def create_exercise(body: ExerciseCreate, db: Session = Depends(get_db)):
    svc = ExerciseService(db)
    ex = svc.create(body)
    db.commit()
    db.refresh(ex)
    return _out(ex, svc.auswahl([ex.id]), ProfilService(db).geraete())


@router.put("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, body: ExerciseUpdate, db: Session = Depends(get_db)):
    svc = ExerciseService(db)
    ex = svc.update(exercise_id, body)
    db.commit()
    db.refresh(ex)
    return _out(ex, svc.auswahl([ex.id]), ProfilService(db).geraete())


@router.patch("/{exercise_id}/select", response_model=ExerciseOut)
def toggle_exercise_selected(exercise_id: int, body: ExerciseSelectUpdate, db: Session = Depends(get_db)):
    svc = ExerciseService(db)
    ex = svc.auswahl_setzen(exercise_id, body.is_selected)
    db.commit()
    db.refresh(ex)
    return _out(ex, svc.auswahl([ex.id]), ProfilService(db).geraete())


@router.delete("/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    svc = ExerciseService(db)
    svc.delete(exercise_id)
    db.commit()
