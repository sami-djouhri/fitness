"""Workout tracking routes."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlanExercise, Workout, WorkoutSet
from app.schemas import (
    WorkoutCreate, WorkoutUpdate, WorkoutOut, WorkoutListOut,
    WorkoutSetCreate, WorkoutSetUpdate, WorkoutSetOut,
    ExerciseHistorySession, OverloadSuggestion, LastWeightEntry, PlanTargetOut,
)
from app.services import aktivitaet
from app.services.workouts import WorkoutService

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


def _set_out(s: WorkoutSet) -> WorkoutSetOut:
    return WorkoutSetOut(
        id=s.id,
        exercise_id=s.exercise_id,
        exercise_name=s.exercise.name if s.exercise else "",
        set_number=s.set_number,
        weight_kg=s.weight_kg,
        reps=s.reps,
        duration_seconds=s.duration_seconds,
        distance_meters=s.distance_meters,
        rpe=s.rpe,
        is_warmup=s.is_warmup,
        set_type=s.set_type,
        group_id=s.group_id,
        notes=s.notes,
        is_completed=s.is_completed,
        completed_at=s.completed_at,
    )


def _plan_target_out(pe: PlanExercise) -> PlanTargetOut:
    return PlanTargetOut(
        exercise_id=pe.exercise_id,
        exercise_name=pe.exercise.name if pe.exercise else "",
        target_sets=pe.target_sets,
        target_reps_min=pe.target_reps_min,
        target_reps_max=pe.target_reps_max,
        target_rpe=pe.target_rpe,
        rest_seconds=pe.rest_seconds,
        notes=pe.notes,
    )


def _workout_out(w: Workout, plan_targets: list[PlanExercise] | None = None) -> WorkoutOut:
    return WorkoutOut(
        id=w.id,
        plan_day_id=w.plan_day_id,
        plan_day_name=w.plan_day.name if w.plan_day else None,
        name=w.name,
        started_at=w.started_at,
        finished_at=w.finished_at,
        notes=w.notes,
        rating=w.rating,
        fatigue_level=w.fatigue_level,
        sleep_quality=w.sleep_quality,
        motivation=w.motivation,
        pre_notes=w.pre_notes,
        sets=[_set_out(s) for s in w.sets],
        plan_targets=[_plan_target_out(pe) for pe in (plan_targets or [])],
    )


@router.get("", response_model=list[WorkoutListOut])
def list_workouts(
    date_from: str | None = None,
    date_to: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = WorkoutService(db)
    workouts = svc.list_all(date_from=date_from, date_to=date_to, skip=skip, limit=limit)
    return [
        WorkoutListOut(
            id=w.id,
            name=w.name,
            started_at=w.started_at,
            finished_at=w.finished_at,
            rating=w.rating,
            set_count=len(w.sets),
        )
        for w in workouts
    ]


@router.post("", response_model=WorkoutOut, status_code=201)
def create_workout(body: WorkoutCreate, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    workout = svc.create(body)
    db.commit()
    db.refresh(workout)
    return _workout_out(workout, svc.plan_targets(workout))


@router.get("/suggestions", response_model=OverloadSuggestion)
def get_suggestions(exercise_id: int, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    return svc.get_overload_suggestion(exercise_id)


@router.get("/last-weights", response_model=list[LastWeightEntry])
def get_last_weights(exercise_ids: list[int] = Query(...), db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    return svc.get_last_weights(exercise_ids)


@router.get("/{workout_id}", response_model=WorkoutOut)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    workout = svc.get(workout_id)
    return _workout_out(workout, svc.plan_targets(workout))


@router.put("/{workout_id}", response_model=WorkoutOut)
def update_workout(workout_id: int, body: WorkoutUpdate, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    workout = svc.update(workout_id, body)
    db.commit()
    db.refresh(workout)
    return _workout_out(workout, svc.plan_targets(workout))


@router.post("/{workout_id}/finish", response_model=WorkoutOut)
def finish_workout(
    workout_id: int,
    hintergrund: BackgroundTasks,
    db: Session = Depends(get_db),
):
    svc = WorkoutService(db)
    workout = svc.finish(workout_id)
    db.commit()
    db.refresh(workout)

    # Ein beendetes Training aendert die Haeufigkeit und damit den
    # Kalorienbedarf. MealPrep rechnet mit dieser Stufe; vorher stand dort ein
    # von Hand gesetztes Auswahlfeld, das nichts vom Training wusste.
    # Uebertragen wird nur bei echter Aenderung der Stufe, nicht bei jedem
    # Training: es ist ein Schreibzugriff in ein fremdes Profil.
    niveau = aktivitaet.ableiten(db)
    if aktivitaet.uebertragen_faellig(db, niveau):
        aktivitaet.uebertragung_vermerken(db, niveau)
        db.commit()
        hintergrund.add_task(
            aktivitaet.an_mealprep, niveau, db.info.get("owner_sub") or "",
        )

    return _workout_out(workout, svc.plan_targets(workout))


@router.delete("/{workout_id}", status_code=204)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    svc.delete(workout_id)
    db.commit()


@router.post("/{workout_id}/sets", response_model=WorkoutSetOut, status_code=201)
def add_set(workout_id: int, body: WorkoutSetCreate, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    ws = svc.add_set(workout_id, body)
    db.commit()
    db.refresh(ws)
    return _set_out(ws)


@router.put("/sets/{set_id}", response_model=WorkoutSetOut)
def update_set(set_id: int, body: WorkoutSetUpdate, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    ws = svc.update_set(set_id, body)
    db.commit()
    db.refresh(ws)
    return _set_out(ws)


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(set_id: int, db: Session = Depends(get_db)):
    svc = WorkoutService(db)
    svc.delete_set(set_id)
    db.commit()
