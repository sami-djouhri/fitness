"""Progress & statistics service."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models import BodyMetric, Exercise, PersonalRecord, Plan, PlanDay, Workout, WorkoutSet
from app.schemas import (
    CalendarDay, ExerciseProgressPoint, VolumeSummary, DashboardSummary,
    MuscleGroupFreshness, MuscleFreshnessResponse,
    ExerciseRecommendation, RecommendationsResponse,
    MuscleVolumeResponse, MuscleVolumeWeek,
    PersonalRecordOut, StrengthLevelOut,
    ReadinessDayAverage, ReadinessCorrelation, ReadinessAnalyticsResponse,
)
from app.services import kalender_adapter
from app.services.satzfilter import arbeitssatz, arbeitssatz_klausel
from app.services.muscle_map import (
    ALL_REGIONS, MUSCLE_TO_REGION, REGION_LABELS, REGION_TO_MUSCLES,
    REGION_TO_PPL, PPL_CATEGORIES, IDEAL_PPL_SPLIT, get_freshness_color,
)


def _estimate_1rm(weight: float, reps: int) -> float:
    """Epley formula for estimated 1RM."""
    if reps <= 0 or weight <= 0:
        return 0
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30), 1)


# Load strength standards from JSON config
_STRENGTH_STANDARDS: dict[str, dict[str, float]] | None = None


def _get_strength_standards() -> dict[str, dict[str, float]]:
    global _STRENGTH_STANDARDS
    if _STRENGTH_STANDARDS is None:
        path = Path(__file__).parent.parent / "data" / "strength_standards.json"
        if path.exists():
            _STRENGTH_STANDARDS = json.loads(path.read_text())
        else:
            _STRENGTH_STANDARDS = {}
    return _STRENGTH_STANDARDS


class ProgressService:
    def __init__(self, db: Session, kalender=None):
        self.db = db
        # Einspeisbar, damit Tests den Kalender setzen koennen, ohne einen
        # Dienst zu brauchen. Ohne Konfiguration ist der Adapter still.
        self._kalender = kalender or kalender_adapter.KalenderAdapter()

    def exercise_progress(self, exercise_id: int, days: int = 90) -> list[ExerciseProgressPoint]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        sets = (
            self.db.query(WorkoutSet, Workout.started_at)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(
                WorkoutSet.exercise_id == exercise_id,
                *arbeitssatz(),
                Workout.started_at >= cutoff,
            )
            .order_by(Workout.started_at)
            .all()
        )
        if not sets:
            return []

        by_date: dict[date, list] = {}
        for ws, started_at in sets:
            d = started_at.date() if isinstance(started_at, datetime) else started_at
            by_date.setdefault(d, []).append(ws)

        result: list[ExerciseProgressPoint] = []
        for d, day_sets in sorted(by_date.items()):
            best_1rm = 0.0
            best_weight = 0.0
            best_reps = 0
            total_vol = 0.0
            for s in day_sets:
                w = s.weight_kg or 0
                r = s.reps or 0
                vol = w * r
                total_vol += vol
                e1rm = _estimate_1rm(w, r)
                if e1rm > best_1rm:
                    best_1rm = e1rm
                    best_weight = w
                    best_reps = r

            result.append(ExerciseProgressPoint(
                date=d,
                estimated_1rm=best_1rm if best_1rm > 0 else None,
                best_set_weight=best_weight if best_weight > 0 else None,
                best_set_reps=best_reps if best_reps > 0 else None,
                total_volume=round(total_vol, 1),
            ))
        return result

    def weekly_volume(self, weeks: int = 12) -> list[VolumeSummary]:
        cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        rows = (
            self.db.query(Workout, WorkoutSet)
            .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
            .filter(
                Workout.started_at >= cutoff,
                *arbeitssatz(),
            )
            .all()
        )
        if not rows:
            return []

        by_week: dict[date, dict] = {}
        for workout, ws in rows:
            d = workout.started_at
            if isinstance(d, datetime):
                d = d.date()
            week_start = d - timedelta(days=d.weekday())
            entry = by_week.setdefault(week_start, {"volume": 0.0, "sets": 0, "workout_ids": set()})
            entry["volume"] += (ws.weight_kg or 0) * (ws.reps or 0)
            entry["sets"] += 1
            entry["workout_ids"].add(ws.workout_id)

        return [
            VolumeSummary(
                week_start=ws,
                total_volume=round(data["volume"], 1),
                total_sets=data["sets"],
                workouts=len(data["workout_ids"]),
            )
            for ws, data in sorted(by_week.items())
        ]

    def dashboard_summary(self) -> DashboardSummary:
        now = datetime.now(timezone.utc)
        cutoff_7 = now - timedelta(days=7)
        cutoff_30 = now - timedelta(days=30)

        workouts_7d = self.db.query(Workout).filter(Workout.started_at >= cutoff_7).count()
        workouts_30d = self.db.query(Workout).filter(Workout.started_at >= cutoff_30).count()

        vol_rows = (
            self.db.query(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps))
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(
                Workout.started_at >= cutoff_7,
                *arbeitssatz(),
                WorkoutSet.weight_kg.isnot(None),
                WorkoutSet.reps.isnot(None),
            )
            .scalar()
        )
        total_volume_7d = round(vol_rows or 0, 1)

        last = self.db.query(Workout).order_by(Workout.started_at.desc()).first()

        streak = 0
        if last:
            check_date = now.date()
            while True:
                has = (
                    self.db.query(Workout)
                    .filter(func.date(Workout.started_at) == check_date.isoformat())
                    .first()
                )
                if has:
                    streak += 1
                    check_date -= timedelta(days=1)
                elif streak == 0:
                    check_date -= timedelta(days=1)
                    has_yesterday = (
                        self.db.query(Workout)
                        .filter(func.date(Workout.started_at) == check_date.isoformat())
                        .first()
                    )
                    if has_yesterday:
                        streak += 1
                        check_date -= timedelta(days=1)
                    else:
                        break
                else:
                    break

        naechster = self._naechster_trainingstag_objekt()

        # Tagestyp aus dem Kalender. Er tauscht den Vorschlag NICHT aus, er
        # weist ihn an einem Feiertag oder im Urlaub nur als nicht
        # selbstverstaendlich aus. Faellt der Kalender aus, bleibt beides
        # leer und die App sagt zum Tag nichts.
        tagestyp = self._kalender.tagestyp(now.date())
        tagestyp_hinweis = kalender_adapter.hinweis(
            tagestyp, naechster.name if naechster else None
        )

        return DashboardSummary(
            workouts_7d=workouts_7d,
            workouts_30d=workouts_30d,
            total_volume_7d=total_volume_7d,
            current_streak=streak,
            last_workout=last.started_at if last else None,
            next_plan_day=naechster.name if naechster else None,
            next_plan_day_id=naechster.id if naechster else None,
            tagestyp=tagestyp,
            tagestyp_hinweis=tagestyp_hinweis,
            vorschlag_optional=tagestyp in kalender_adapter.FREIE_TAGE,
        )

    # -------------------------------------------------------------------
    # Welcher Trainingstag ist dran
    # -------------------------------------------------------------------

    def _naechster_trainingstag_objekt(self) -> PlanDay | None:
        """Der Trainingstag, der als naechstes ansteht.

        ``next_plan_day`` stand seit Bestehen in beiden Schemas und wurde nie
        gefuellt. Damit fehlte die Antwort auf die einzige Frage, die man beim
        Oeffnen der App hat: was ist heute dran?

        Zwei Wege, in dieser Reihenfolge:

        1. Hat ein Tag einen festen Wochentag, gilt der. Das ist die
           ausdrueckliche Angabe des Nutzers und schlaegt jede Ableitung.
        2. Sonst Rotation: der Tag nach dem, der zuletzt trainiert wurde. So
           arbeitet ein Push/Pull/Legs-Plan ohne festen Kalender.
        """
        plan = self.db.query(Plan).filter(Plan.is_active == True).first()  # noqa: E712
        if not plan:
            return None
        tage = sorted(plan.days, key=lambda d: (d.sort_order, d.id))
        if not tage:
            return None

        heute = datetime.now(timezone.utc).weekday()
        fuer_heute = [t for t in tage if t.day_of_week == heute]
        if fuer_heute:
            return fuer_heute[0]

        # Rotation: letztes Workout, das einem Tag dieses Plans zugeordnet war.
        tag_ids = [t.id for t in tage]
        letztes = (
            self.db.query(Workout)
            .filter(Workout.plan_day_id.in_(tag_ids))
            .order_by(Workout.started_at.desc())
            .first()
        )
        if not letztes:
            return tage[0]
        stelle = next((i for i, t in enumerate(tage) if t.id == letztes.plan_day_id), None)
        if stelle is None:
            return tage[0]
        return tage[(stelle + 1) % len(tage)]



    # -------------------------------------------------------------------
    # Muscle freshness
    # -------------------------------------------------------------------

    def muscle_freshness(self) -> MuscleFreshnessResponse:
        """How recently was each muscle region trained, and how hard?

        Used by the dashboard to suggest which body parts deserve attention
        next. Returns one row per region (chest, back, …) with:

        - ``days_since_trained``: days since the most recent non-warmup set
          touched a muscle that maps into the region. None = never trained.
        - ``total_volume_last``: sum of ``weight_kg × reps`` across all sets
          on that latest training date (single-day total, not cumulative).
        - ``color``: UI-Hint via ``get_freshness_color`` (fresh / training-due
          / overdue / cold).
        - ``exercises_available``: count of exercises in the catalog that
          target this region at all (primary or secondary). Helps the UI hint
          "no exercises configured" vs "trained recently".

        Algorithm:

        1. Pull all non-warmup sets joined with their workout and exercise.
        2. For each set, project every primary + secondary muscle through
           ``MUSCLE_TO_REGION`` (one muscle may map to multiple regions,
           e.g. "shoulders_front" → ["shoulders", "push"]).
        3. Per region, track the latest workout date and the cumulative
           volume on that single latest date.
        4. In a second pass, count how many catalog exercises hit each region
           (independent of training history).
        5. Compose one ``MuscleGroupFreshness`` per region in ``ALL_REGIONS``.

        Cost: O(W × M) where W = workout-sets, M = avg muscles/exercise.
        On a personal lager (~5k sets) negligible. If this becomes hot,
        push the projection into SQL via a join + aggregate.
        """
        now = datetime.now(timezone.utc)
        today = now.date()

        rows = (
            self.db.query(WorkoutSet, Workout, Exercise)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(*arbeitssatz())
            .all()
        )

        region_last: dict[str, date] = {}
        region_volume: dict[str, float] = {}

        for ws, workout, exercise in rows:
            w_date = workout.started_at
            if isinstance(w_date, datetime):
                w_date = w_date.date()
            vol = (ws.weight_kg or 0) * (ws.reps or 0)

            # Check both primary and secondary muscles
            all_muscles = exercise.primary_muscles + exercise.secondary_muscles
            for muscle in all_muscles:
                mapped = MUSCLE_TO_REGION.get(muscle, [])
                for region in mapped:
                    prev = region_last.get(region)
                    if prev is None or w_date > prev:
                        region_last[region] = w_date
                        region_volume[region] = vol
                    elif w_date == prev:
                        region_volume[region] = region_volume.get(region, 0) + vol

        all_exercises = self.db.query(Exercise).all()
        region_exercise_count: dict[str, int] = {r: 0 for r in ALL_REGIONS}
        for ex in all_exercises:
            seen_regions: set[str] = set()
            for muscle in ex.primary_muscles + ex.secondary_muscles:
                for region in MUSCLE_TO_REGION.get(muscle, []):
                    seen_regions.add(region)
            for region in seen_regions:
                region_exercise_count[region] += 1

        regions = []
        for region in ALL_REGIONS:
            last_date = region_last.get(region)
            days = (today - last_date).days if last_date else None
            regions.append(MuscleGroupFreshness(
                region=region,
                label=REGION_LABELS[region],
                days_since_trained=days,
                color=get_freshness_color(days),
                total_volume_last=round(region_volume.get(region, 0), 1),
                exercises_available=region_exercise_count.get(region, 0),
            ))

        summary = self.dashboard_summary()

        return MuscleFreshnessResponse(
            regions=regions,
            workouts_this_week=summary.workouts_7d,
            current_streak=summary.current_streak,
        )

    # -------------------------------------------------------------------
    # Recommendations
    # -------------------------------------------------------------------

    def recommendations(self) -> RecommendationsResponse:
        freshness = self.muscle_freshness()
        now = datetime.now(timezone.utc)
        cutoff_30 = now - timedelta(days=30)

        rows_30d = (
            self.db.query(WorkoutSet, Exercise)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(
                *arbeitssatz(),
                Workout.started_at >= cutoff_30,
            )
            .all()
        )

        ppl_counts: dict[str, int] = {cat: 0 for cat in PPL_CATEGORIES}
        for ws, exercise in rows_30d:
            for muscle in exercise.primary_muscles:
                for region in MUSCLE_TO_REGION.get(muscle, []):
                    cat = REGION_TO_PPL.get(region)
                    if cat:
                        ppl_counts[cat] += 1

        total_sets = sum(ppl_counts.values()) or 1
        muscle_balance = {cat: round(cnt / total_sets, 2) for cat, cnt in ppl_counts.items()}

        region_scores: list[tuple[str, float]] = []
        freshness_map = {r.region: r for r in freshness.regions}

        for region in ALL_REGIONS:
            rf = freshness_map[region]
            days = rf.days_since_trained

            if days is None:
                staleness = 100.0
            else:
                staleness = min(days * 10, 100)

            cat = REGION_TO_PPL.get(region, "core")
            actual = muscle_balance.get(cat, 0)
            ideal = IDEAL_PPL_SPLIT.get(cat, 0.1)
            imbalance_bonus = max(0, (ideal - actual) / ideal) * 30

            score = staleness + imbalance_bonus
            region_scores.append((region, score))

        region_scores.sort(key=lambda x: x[1], reverse=True)
        top_regions = region_scores[:4]

        all_exercises = self.db.query(Exercise).all()
        recommendations: list[ExerciseRecommendation] = []
        seen_exercise_ids: set[int] = set()

        for region, region_score in top_regions:
            rf = freshness_map[region]
            target_muscles = set(REGION_TO_MUSCLES.get(region, []))

            candidates = []
            for ex in all_exercises:
                if ex.id in seen_exercise_ids:
                    continue
                ex_muscles = set(ex.primary_muscles)
                if ex_muscles & target_muscles:
                    compound_bonus = 10 if ex.is_compound else 0
                    candidates.append((ex, region_score + compound_bonus))

            candidates.sort(key=lambda x: x[1], reverse=True)
            for ex, score in candidates[:2]:
                seen_exercise_ids.add(ex.id)
                days = rf.days_since_trained
                if days is None:
                    reason = f"{rf.label} noch nie trainiert"
                elif days >= 7:
                    reason = f"{rf.label} seit {days} Tagen nicht trainiert"
                elif days >= 5:
                    reason = f"{rf.label} wird fällig ({days} Tage)"
                else:
                    cat = REGION_TO_PPL.get(region, "core")
                    actual_pct = muscle_balance.get(cat, 0)
                    ideal_pct = IDEAL_PPL_SPLIT.get(cat, 0.1)
                    if actual_pct < ideal_pct * 0.8:
                        cat_label = {"push": "Push", "pull": "Pull", "legs": "Beine", "core": "Core"}.get(cat, cat)
                        reason = f"{cat_label}-Anteil unterrepräsentiert"
                    else:
                        reason = f"{rf.label} für Balance empfohlen"

                recommendations.append(ExerciseRecommendation(
                    exercise_id=ex.id,
                    exercise_name=ex.name,
                    category=ex.category,
                    primary_muscles=ex.primary_muscles,
                    is_compound=ex.is_compound,
                    reason=reason,
                    priority_score=round(score, 1),
                ))

        recommendations.sort(key=lambda x: x.priority_score, reverse=True)

        return RecommendationsResponse(
            recommendations=recommendations[:8],
            muscle_balance=muscle_balance,
        )

    # -------------------------------------------------------------------
    # Personal Records
    # -------------------------------------------------------------------

    def get_prs(self, exercise_id: int | None = None) -> list[PersonalRecordOut]:
        q = self.db.query(PersonalRecord).join(Exercise, PersonalRecord.exercise_id == Exercise.id)
        if exercise_id:
            q = q.filter(PersonalRecord.exercise_id == exercise_id)
        prs = q.order_by(PersonalRecord.exercise_id, PersonalRecord.pr_type).all()
        return [
            PersonalRecordOut(
                id=pr.id,
                exercise_id=pr.exercise_id,
                exercise_name=pr.exercise.name,
                pr_type=pr.pr_type,
                value=pr.value,
                achieved_at=pr.achieved_at,
                workout_set_id=pr.workout_set_id,
            )
            for pr in prs
        ]

    def get_recent_prs(self, limit: int = 10) -> list[PersonalRecordOut]:
        prs = (
            self.db.query(PersonalRecord)
            .join(Exercise, PersonalRecord.exercise_id == Exercise.id)
            .order_by(desc(PersonalRecord.achieved_at))
            .limit(limit)
            .all()
        )
        return [
            PersonalRecordOut(
                id=pr.id,
                exercise_id=pr.exercise_id,
                exercise_name=pr.exercise.name,
                pr_type=pr.pr_type,
                value=pr.value,
                achieved_at=pr.achieved_at,
                workout_set_id=pr.workout_set_id,
            )
            for pr in prs
        ]

    # -------------------------------------------------------------------
    # Volume per muscle group
    # -------------------------------------------------------------------

    def volume_per_muscle(self, weeks: int = 4) -> MuscleVolumeResponse:
        cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        rows = (
            self.db.query(WorkoutSet, Workout, Exercise)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(
                Workout.started_at >= cutoff,
                *arbeitssatz(),
            )
            .all()
        )

        # week_start -> region -> {sets, volume}
        by_week: dict[date, dict[str, dict]] = {}
        for ws, workout, exercise in rows:
            d = workout.started_at
            if isinstance(d, datetime):
                d = d.date()
            week_start = d - timedelta(days=d.weekday())

            vol = (ws.weight_kg or 0) * (ws.reps or 0)
            for muscle in exercise.primary_muscles:
                for region in MUSCLE_TO_REGION.get(muscle, []):
                    entry = by_week.setdefault(week_start, {}).setdefault(
                        region, {"sets": 0, "volume": 0.0}
                    )
                    entry["sets"] += 1
                    entry["volume"] += vol

        result_weeks = []
        for week_start in sorted(by_week.keys()):
            muscles = []
            for region in ALL_REGIONS:
                data = by_week[week_start].get(region, {"sets": 0, "volume": 0.0})
                muscles.append(MuscleVolumeWeek(
                    region=region,
                    label=REGION_LABELS[region],
                    sets=data["sets"],
                    volume=round(data["volume"], 1),
                ))
            result_weeks.append({
                "week_start": week_start.isoformat(),
                "muscles": [m.model_dump() for m in muscles],
            })

        return MuscleVolumeResponse(weeks=result_weeks)

    # -------------------------------------------------------------------
    # Calendar heatmap
    # -------------------------------------------------------------------

    def calendar_heatmap(self, months: int = 3) -> list[CalendarDay]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
        rows = (
            self.db.query(Workout, func.count(WorkoutSet.id).label("set_count"))
            # Bedingung in die ON-Klausel, nicht ins WHERE: sonst verschwinden
            # Workouts ohne gezaehlten Satz ganz aus der Heatmap, statt mit
            # null Saetzen zu erscheinen.
            .outerjoin(WorkoutSet, and_(
                WorkoutSet.workout_id == Workout.id,
                arbeitssatz_klausel(),
            ))
            .filter(Workout.started_at >= cutoff)
            .group_by(Workout.id)
            .all()
        )

        by_date: dict[date, dict] = {}
        for workout, set_count in rows:
            d = workout.started_at
            if isinstance(d, datetime):
                d = d.date()
            entry = by_date.setdefault(d, {"workouts": 0, "sets": 0})
            entry["workouts"] += 1
            entry["sets"] += set_count or 0

        return [
            CalendarDay(date=d, workouts=data["workouts"], sets=data["sets"])
            for d, data in sorted(by_date.items())
        ]

    # -------------------------------------------------------------------
    # Strength standards
    # -------------------------------------------------------------------

    def strength_level(self, exercise_id: int) -> StrengthLevelOut:
        exercise = self.db.get(Exercise, exercise_id)
        if not exercise:
            return StrengthLevelOut(exercise_id=exercise_id, exercise_name="")

        standards = _get_strength_standards()
        levels = standards.get(exercise.name, {})

        # Get current 1RM from PRs
        pr = (
            self.db.query(PersonalRecord)
            .filter(
                PersonalRecord.exercise_id == exercise_id,
                PersonalRecord.pr_type == "1rm",
            )
            .first()
        )
        current_1rm = pr.value if pr else None

        # Get latest body weight
        latest_bm = self.db.query(BodyMetric).order_by(desc(BodyMetric.date)).first()
        body_weight = latest_bm.weight_kg if latest_bm else None

        ratio = None
        level = "unbekannt"
        if current_1rm and body_weight and body_weight > 0:
            ratio = round(current_1rm / body_weight, 2)
            if levels:
                if ratio >= levels.get("elite", 999):
                    level = "elite"
                elif ratio >= levels.get("advanced", 999):
                    level = "fortgeschritten"
                elif ratio >= levels.get("intermediate", 999):
                    level = "mittel"
                elif ratio >= levels.get("beginner", 999):
                    level = "anfänger"
                else:
                    level = "einsteiger"

        return StrengthLevelOut(
            exercise_id=exercise_id,
            exercise_name=exercise.name,
            current_1rm=current_1rm,
            body_weight=body_weight,
            ratio=ratio,
            level=level,
            levels=levels,
        )

    # -------------------------------------------------------------------
    # Readiness analytics
    # -------------------------------------------------------------------

    def get_readiness_analytics(self, days: int = 30) -> ReadinessAnalyticsResponse:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # All workouts in the period
        all_workouts = (
            self.db.query(Workout)
            .filter(Workout.started_at >= cutoff)
            .all()
        )

        with_readiness = [
            w for w in all_workouts if w.fatigue_level is not None
        ]
        without_readiness = len(all_workouts) - len(with_readiness)

        # Daily averages
        by_date: dict[date, list[Workout]] = {}
        for w in with_readiness:
            d = w.started_at
            if isinstance(d, datetime):
                d = d.date()
            by_date.setdefault(d, []).append(w)

        daily_averages: list[ReadinessDayAverage] = []
        for d, day_workouts in sorted(by_date.items()):
            fatigue_vals = [w.fatigue_level for w in day_workouts if w.fatigue_level is not None]
            sleep_vals = [w.sleep_quality for w in day_workouts if w.sleep_quality is not None]
            motivation_vals = [w.motivation for w in day_workouts if w.motivation is not None]

            if fatigue_vals or sleep_vals or motivation_vals:
                daily_averages.append(ReadinessDayAverage(
                    date=d,
                    avg_fatigue=round(sum(fatigue_vals) / len(fatigue_vals), 1) if fatigue_vals else 0,
                    avg_sleep=round(sum(sleep_vals) / len(sleep_vals), 1) if sleep_vals else 0,
                    avg_motivation=round(sum(motivation_vals) / len(motivation_vals), 1) if motivation_vals else 0,
                    workout_count=len(day_workouts),
                ))

        # Volume per workout helper
        def _workout_total_volume(workout_id: int) -> float:
            vol = (
                self.db.query(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps))
                .filter(
                    WorkoutSet.workout_id == workout_id,
                    *arbeitssatz(),
                    WorkoutSet.weight_kg.isnot(None),
                    WorkoutSet.reps.isnot(None),
                )
                .scalar()
            )
            return float(vol) if vol else 0.0

        # Sleep correlation: high (>=4) vs low (<=2)
        high_sleep = [w for w in with_readiness if w.sleep_quality is not None and w.sleep_quality >= 4]
        low_sleep = [w for w in with_readiness if w.sleep_quality is not None and w.sleep_quality <= 2]

        high_sleep_vols = [_workout_total_volume(w.id) for w in high_sleep]
        low_sleep_vols = [_workout_total_volume(w.id) for w in low_sleep]

        sleep_correlation = ReadinessCorrelation(
            high_avg_volume=round(sum(high_sleep_vols) / len(high_sleep_vols), 1) if high_sleep_vols else None,
            low_avg_volume=round(sum(low_sleep_vols) / len(low_sleep_vols), 1) if low_sleep_vols else None,
            high_workout_count=len(high_sleep),
            low_workout_count=len(low_sleep),
        )

        # Fatigue correlation: high fatigue (>=4) vs low fatigue (<=2)
        high_fatigue = [w for w in with_readiness if w.fatigue_level is not None and w.fatigue_level >= 4]
        low_fatigue = [w for w in with_readiness if w.fatigue_level is not None and w.fatigue_level <= 2]

        high_fatigue_vols = [_workout_total_volume(w.id) for w in high_fatigue]
        low_fatigue_vols = [_workout_total_volume(w.id) for w in low_fatigue]

        fatigue_correlation = ReadinessCorrelation(
            high_avg_volume=round(sum(high_fatigue_vols) / len(high_fatigue_vols), 1) if high_fatigue_vols else None,
            low_avg_volume=round(sum(low_fatigue_vols) / len(low_fatigue_vols), 1) if low_fatigue_vols else None,
            high_workout_count=len(high_fatigue),
            low_workout_count=len(low_fatigue),
        )

        return ReadinessAnalyticsResponse(
            daily_averages=daily_averages,
            sleep_correlation=sleep_correlation,
            fatigue_correlation=fatigue_correlation,
            workouts_with_readiness=len(with_readiness),
            workouts_without_readiness=without_readiness,
        )
