"""Tests for progress & statistics service."""

from datetime import date, datetime, timedelta, timezone

from app.models import Exercise, Workout, WorkoutSet
from app.services.progress import ProgressService, _estimate_1rm


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _exercise(db_session, name="Bankdrücken", muscles=("Brust",), category="Brust"):
    ex = Exercise(
        name=name,
        category=category,
        equipment="Langhantel",
        is_compound=True,
    )
    ex.primary_muscles = list(muscles)
    db_session.add(ex)
    db_session.flush()
    return ex


def _workout(db_session, started_at=None, finished=True):
    started = started_at or datetime.now(timezone.utc)
    w = Workout(name="Test", started_at=started)
    if finished:
        w.finished_at = started + timedelta(minutes=45)
    db_session.add(w)
    db_session.flush()
    return w


def _set(db_session, workout, exercise, weight, reps, set_number=1, warmup=False):
    s = WorkoutSet(
        workout_id=workout.id,
        exercise_id=exercise.id,
        set_number=set_number,
        weight_kg=weight,
        reps=reps,
        is_warmup=warmup,
    )
    db_session.add(s)
    db_session.flush()
    return s


# -----------------------------------------------------------------------------
# Pure helpers
# -----------------------------------------------------------------------------

def test_estimate_1rm_single_rep_returns_weight():
    assert _estimate_1rm(100.0, 1) == 100.0


def test_estimate_1rm_epley_formula():
    # 100kg × 5 reps → Epley: 100 * (1 + 5/30) = 116.666… ≈ 116.7
    assert _estimate_1rm(100.0, 5) == 116.7


def test_estimate_1rm_invalid_inputs():
    assert _estimate_1rm(0.0, 5) == 0
    assert _estimate_1rm(100.0, 0) == 0
    assert _estimate_1rm(-50.0, 5) == 0


# -----------------------------------------------------------------------------
# dashboard_summary
# -----------------------------------------------------------------------------

def test_dashboard_summary_empty(db_session):
    summary = ProgressService(db_session).dashboard_summary()
    assert summary.workouts_7d == 0
    assert summary.workouts_30d == 0
    assert summary.total_volume_7d == 0
    assert summary.current_streak == 0
    assert summary.last_workout is None


def test_dashboard_summary_with_workout(db_session):
    ex = _exercise(db_session)
    w = _workout(db_session)
    _set(db_session, w, ex, weight=80.0, reps=10)
    _set(db_session, w, ex, weight=80.0, reps=8, set_number=2)

    summary = ProgressService(db_session).dashboard_summary()
    assert summary.workouts_7d == 1
    assert summary.workouts_30d == 1
    # 80 × 10 + 80 × 8 = 1440
    assert summary.total_volume_7d == 1440.0
    assert summary.last_workout is not None


def test_dashboard_summary_ignores_warmup(db_session):
    ex = _exercise(db_session)
    w = _workout(db_session)
    _set(db_session, w, ex, weight=40.0, reps=10, warmup=True)
    _set(db_session, w, ex, weight=80.0, reps=10, set_number=2)

    summary = ProgressService(db_session).dashboard_summary()
    assert summary.total_volume_7d == 800.0


# -----------------------------------------------------------------------------
# exercise_progress
# -----------------------------------------------------------------------------

def test_exercise_progress_picks_best_1rm_per_day(db_session):
    ex = _exercise(db_session)
    w = _workout(db_session)
    # Best set is 100×5 → 1RM ≈ 116.7
    _set(db_session, w, ex, weight=80.0, reps=10, set_number=1)
    _set(db_session, w, ex, weight=100.0, reps=5, set_number=2)
    _set(db_session, w, ex, weight=90.0, reps=6, set_number=3)

    points = ProgressService(db_session).exercise_progress(ex.id, days=90)
    assert len(points) == 1
    assert points[0].estimated_1rm == 116.7
    assert points[0].best_set_weight == 100.0
    assert points[0].best_set_reps == 5
    # total volume = 80*10 + 100*5 + 90*6 = 800 + 500 + 540 = 1840
    assert points[0].total_volume == 1840.0


def test_exercise_progress_returns_empty_when_no_sets(db_session):
    ex = _exercise(db_session)
    points = ProgressService(db_session).exercise_progress(ex.id)
    assert points == []


# -----------------------------------------------------------------------------
# weekly_volume
# -----------------------------------------------------------------------------

def test_weekly_volume_groups_by_week(db_session):
    ex = _exercise(db_session)
    w = _workout(db_session)
    _set(db_session, w, ex, weight=100.0, reps=5)

    volumes = ProgressService(db_session).weekly_volume(weeks=12)
    assert len(volumes) == 1
    assert volumes[0].total_volume == 500.0
    assert volumes[0].total_sets == 1
    assert volumes[0].workouts == 1


def test_weekly_volume_empty(db_session):
    assert ProgressService(db_session).weekly_volume() == []


# -----------------------------------------------------------------------------
# muscle_freshness
# -----------------------------------------------------------------------------

def test_muscle_freshness_empty_has_all_regions_with_none_days(db_session):
    response = ProgressService(db_session).muscle_freshness()
    assert len(response.regions) > 0
    assert all(r.days_since_trained is None for r in response.regions)


def test_muscle_freshness_marks_trained_region(db_session):
    ex = _exercise(db_session, name="Bankdrücken", muscles=("Brust",))
    w = _workout(db_session)
    _set(db_session, w, ex, weight=80.0, reps=10)

    response = ProgressService(db_session).muscle_freshness()
    trained = [r for r in response.regions if r.days_since_trained == 0]
    assert any(r.region == "chest" for r in trained), "Chest region should be marked trained today"


# -----------------------------------------------------------------------------
# recommendations
# -----------------------------------------------------------------------------

def test_recommendations_shape(db_session):
    _exercise(db_session, name="Bankdrücken", muscles=("Brust",), category="Brust")
    response = ProgressService(db_session).recommendations()
    assert response.muscle_balance is not None
    assert response.recommendations is not None
