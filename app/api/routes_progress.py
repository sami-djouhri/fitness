"""Progress & statistics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AktivitaetsniveauOut,
    ExerciseProgressPoint, VolumeSummary, DashboardSummary,
    MuscleFreshnessResponse, RecommendationsResponse,
    PersonalRecordOut, ExerciseHistorySession, WorkoutSetOut,
    CalendarDay, StrengthLevelOut,
    MuscleVolumeResponse, ReadinessAnalyticsResponse,
)
from app.services.progress import ProgressService
from app.services import aktivitaet
from app.services.workouts import WorkoutService
from app.models import WorkoutSet

router = APIRouter(prefix="/api/progress", tags=["progress"])


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
    )


@router.get("/exercise/{exercise_id}", response_model=list[ExerciseProgressPoint])
def exercise_progress(
    exercise_id: int,
    days: int = 90,
    db: Session = Depends(get_db),
):
    svc = ProgressService(db)
    return svc.exercise_progress(exercise_id, days=days)


@router.get("/exercise/{exercise_id}/history", response_model=list[ExerciseHistorySession])
def exercise_history(
    exercise_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    svc = WorkoutService(db)
    history = svc.exercise_history(exercise_id, limit=limit)
    return [
        ExerciseHistorySession(
            date=h["date"],
            workout_id=h["workout_id"],
            workout_name=h["workout_name"],
            sets=[_set_out(s) for s in h["sets"]],
        )
        for h in history
    ]


@router.get("/volume", response_model=list[VolumeSummary])
def weekly_volume(weeks: int = 12, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.weekly_volume(weeks=weeks)


@router.get("/volume-per-muscle", response_model=MuscleVolumeResponse)
def volume_per_muscle(weeks: int = 4, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.volume_per_muscle(weeks=weeks)


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.dashboard_summary()


@router.get("/muscle-freshness", response_model=MuscleFreshnessResponse)
def muscle_freshness(db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.muscle_freshness()


@router.get("/recommendations", response_model=RecommendationsResponse)
def recommendations(db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.recommendations()


@router.get("/prs", response_model=list[PersonalRecordOut])
def get_prs(exercise_id: int | None = None, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.get_prs(exercise_id=exercise_id)


@router.get("/prs/recent", response_model=list[PersonalRecordOut])
def get_recent_prs(limit: int = 10, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.get_recent_prs(limit=limit)


@router.get("/calendar", response_model=list[CalendarDay])
def calendar_heatmap(months: int = 3, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.calendar_heatmap(months=months)


@router.get("/readiness", response_model=ReadinessAnalyticsResponse)
def readiness_analytics(days: int = 30, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.get_readiness_analytics(days=days)


@router.get("/strength-level", response_model=StrengthLevelOut)
def strength_level(exercise_id: int, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    return svc.strength_level(exercise_id)


@router.get("/aktivitaetsniveau", response_model=AktivitaetsniveauOut)
def aktivitaetsniveau(db: Session = Depends(get_db)):
    """Was das Training fuer den Kalorienbedarf bedeutet.

    Die Zahl ist die Eingangsgroesse fuer MealPreps Tagesbedarf. Sie hier
    anzuzeigen macht die Kette sichtbar: Training, Bedarf, Gerichte,
    Einkaufsliste.
    """
    n = aktivitaet.ableiten(db)
    return AktivitaetsniveauOut(
        stufe=n.stufe,
        faktor=n.faktor,
        begruendung=n.begruendung,
        trainings_pro_woche=n.trainings_pro_woche,
        trainings_im_fenster=n.trainings_im_fenster,
        fenster_tage=n.fenster_tage,
        belastbar=n.belastbar,
        # Uebertragen gilt als erledigt, wenn nichts mehr faellig ist. Bei zu
        # wenig Daten ist das nie faellig, dann ist auch nichts uebertragen.
        an_mealprep_uebertragen=n.belastbar and not aktivitaet.uebertragen_faellig(db, n),
    )
