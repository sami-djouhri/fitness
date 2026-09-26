"""Training plan routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain import DomainError
from app.models import Plan, PlanDay, PlanExercise
from app.schemas import (
    PlanCreate, PlanUpdate, PlanOut, PlanListOut,
    PlanDayCreate, PlanDayUpdate, PlanDayOut,
    PlanExerciseCreate, PlanExerciseUpdate, PlanExerciseOut,
    PlanvorlageOut,
)
from app.services.plans import PlanService
from app.services.planvorlagen import PlanvorlagenService

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _pe_out(pe: PlanExercise) -> PlanExerciseOut:
    return PlanExerciseOut(
        id=pe.id,
        exercise_id=pe.exercise_id,
        exercise_name=pe.exercise.name if pe.exercise else "",
        sort_order=pe.sort_order,
        target_sets=pe.target_sets,
        target_reps_min=pe.target_reps_min,
        target_reps_max=pe.target_reps_max,
        target_rpe=pe.target_rpe,
        rest_seconds=pe.rest_seconds,
        notes=pe.notes,
    )


def _day_out(d: PlanDay) -> PlanDayOut:
    return PlanDayOut(
        id=d.id,
        name=d.name,
        day_of_week=d.day_of_week,
        sort_order=d.sort_order,
        exercises=[_pe_out(pe) for pe in d.exercises],
    )


def _plan_out(p: Plan) -> PlanOut:
    return PlanOut(
        id=p.id,
        name=p.name,
        description=p.description,
        is_active=p.is_active,
        created_at=p.created_at,
        days=[_day_out(d) for d in p.days],
    )


@router.get("", response_model=list[PlanListOut])
def list_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = PlanService(db)
    plans = svc.list_all(skip=skip, limit=limit)
    return [
        PlanListOut(
            id=p.id,
            name=p.name,
            description=p.description,
            is_active=p.is_active,
            created_at=p.created_at,
            day_count=len(p.days),
        )
        for p in plans
    ]


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(body: PlanCreate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.create(body)
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@router.get("/vorlagen", response_model=list[PlanvorlageOut])
def vorlagen(db: Session = Depends(get_db)):
    """Planvorlagen, die passende zuerst.

    ★ Diese Route muss VOR ``/{plan_id}`` stehen. Sonst versucht FastAPI,
    "vorlagen" als Zahl zu lesen, und liefert eine Fehlermeldung ueber einen
    ungueltigen Pfadparameter statt der Liste.
    """
    svc = PlanvorlagenService(db)
    ergebnis = [PlanvorlageOut(**v) for v in svc.passende_vorlagen()]
    db.commit()
    return ergebnis


@router.post("/vorlagen/{vorlage_id}", response_model=PlanOut, status_code=201)
def vorlage_anlegen(vorlage_id: str, aktivieren: bool = True,
                    db: Session = Depends(get_db)):
    """Aus einer Vorlage einen Plan erzeugen, der zur Ausruestung passt.

    Die Vorlage nennt keine Uebungen, sondern Bausteine ("eine Grunduebung
    fuer die Brust"). Welche Uebung daraus wird, entscheidet der Bestand des
    Nutzers und seine Progressionsstufe. Dieselbe Vorlage ergibt im Studio
    und in der Wohnung deshalb einen anderen, aber jeweils ausfuehrbaren Plan.
    """
    svc = PlanvorlagenService(db)
    try:
        plan = svc.anlegen(vorlage_id, aktivieren=aktivieren)
    except KeyError:
        raise DomainError("Vorlage nicht gefunden", {"vorlage": vorlage_id})
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    return _plan_out(svc.get(plan_id))


@router.put("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, body: PlanUpdate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.update(plan_id, body)
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    svc.delete(plan_id)
    db.commit()


@router.post("/{plan_id}/activate", response_model=PlanOut)
def activate_plan(plan_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.activate(plan_id)
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@router.post("/{plan_id}/days", response_model=PlanDayOut, status_code=201)
def add_day(plan_id: int, body: PlanDayCreate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    day = svc.add_day(plan_id, body)
    db.commit()
    db.refresh(day)
    return _day_out(day)


@router.put("/days/{day_id}", response_model=PlanDayOut)
def update_day(day_id: int, body: PlanDayUpdate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    day = svc.update_day(day_id, body)
    db.commit()
    db.refresh(day)
    return _day_out(day)


@router.delete("/days/{day_id}", status_code=204)
def delete_day(day_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    svc.delete_day(day_id)
    db.commit()


@router.post("/days/{day_id}/exercises", response_model=PlanExerciseOut, status_code=201)
def add_day_exercise(day_id: int, body: PlanExerciseCreate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    pe = svc.add_day_exercise(day_id, body)
    db.commit()
    db.refresh(pe)
    return _pe_out(pe)


@router.put("/day-exercises/{pe_id}", response_model=PlanExerciseOut)
def update_day_exercise(pe_id: int, body: PlanExerciseUpdate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    pe = svc.update_day_exercise(pe_id, body)
    db.commit()
    db.refresh(pe)
    return _pe_out(pe)


@router.delete("/day-exercises/{pe_id}", status_code=204)
def delete_day_exercise(pe_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    svc.delete_day_exercise(pe_id)
    db.commit()
