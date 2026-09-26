"""Workout tracking service."""

from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.domain import DomainError
from app.models import Exercise, PersonalRecord, Workout, WorkoutSet, PlanDay, PlanExercise
from app.schemas import WorkoutCreate, WorkoutUpdate, WorkoutSetCreate, WorkoutSetUpdate
from app.services.satzfilter import arbeitssatz


def _estimate_1rm(weight: float, reps: int) -> float:
    if reps <= 0 or weight <= 0:
        return 0
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30), 1)


class WorkoutService:
    def __init__(self, db: Session):
        self.db = db

    def list_all(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Workout]:
        q = self.db.query(Workout)
        if date_from:
            q = q.filter(Workout.started_at >= date_from)
        if date_to:
            q = q.filter(Workout.started_at <= date_to)
        return q.order_by(Workout.started_at.desc()).offset(skip).limit(limit).all()

    def get(self, workout_id: int) -> Workout:
        workout = (
            self.db.query(Workout)
            .options(joinedload(Workout.sets).joinedload(WorkoutSet.exercise))
            .filter(Workout.id == workout_id)
            .first()
        )
        if not workout:
            raise DomainError("Workout nicht gefunden", {"workout_id": workout_id})
        return workout

    def create(self, data: WorkoutCreate) -> Workout:
        name = data.name
        day = None
        if data.plan_day_id:
            day = self.db.get(PlanDay, data.plan_day_id)
            if not day:
                raise DomainError("Trainingstag nicht gefunden", {"plan_day_id": data.plan_day_id})
            if name == "Workout":
                name = day.name

        workout = Workout(
            plan_day_id=data.plan_day_id,
            name=name,
            notes=data.notes,
            fatigue_level=data.fatigue_level,
            sleep_quality=data.sleep_quality,
            motivation=data.motivation,
            pre_notes=data.pre_notes,
        )
        self.db.add(workout)

        if data.prefill:
            self.db.flush()  # workout.id fuer die Saetze
            if day is not None:
                self._prefill_from_plan_day(workout, data.plan_day_id)
            elif data.exercise_ids:
                self._prefill_from_exercises(workout, data.exercise_ids)

        return workout

    # --- Vorbefuellen ---

    # Saetze je Uebung, wenn keine Plan-Vorgabe existiert (freies Training aus
    # einer Empfehlung). Entspricht dem Standardwert von PlanExercise.target_sets.
    STANDARD_SAETZE = 3

    def _prefill_from_plan_day(self, workout: Workout, plan_day_id: int) -> None:
        """Uebertraegt die Uebungen des Trainingstages in leere Arbeitssaetze.

        Bis 2026-09 uebernahm ``create`` nur den Namen des Tages. Der gepflegte
        Plan half im Gym damit nicht: man startete "Push" und musste jede der
        geplanten Uebungen von Hand aus dem Katalog suchen.
        """
        for pe in self.get_plan_day_exercises(plan_day_id):
            letzte = self._letzte_werte(pe.exercise_id)
            for nummer in range(1, max(1, pe.target_sets) + 1):
                self.db.add(WorkoutSet(
                    workout_id=workout.id,
                    exercise_id=pe.exercise_id,
                    set_number=nummer,
                    weight_kg=letzte[0],
                    reps=letzte[1] or pe.target_reps_min,
                    set_type="normal",
                    is_warmup=False,
                    is_completed=False,
                ))

    def _prefill_from_exercises(self, workout: Workout, exercise_ids: list[int]) -> None:
        """Vorbefuellen aus einer Uebungsliste ohne Plan (Dashboard-Empfehlung)."""
        gesehen: set[int] = set()
        for exercise_id in exercise_ids:
            if exercise_id in gesehen:
                continue
            if not self.db.get(Exercise, exercise_id):
                raise DomainError("Übung nicht gefunden", {"exercise_id": exercise_id})
            gesehen.add(exercise_id)
            letzte = self._letzte_werte(exercise_id)
            for nummer in range(1, self.STANDARD_SAETZE + 1):
                self.db.add(WorkoutSet(
                    workout_id=workout.id,
                    exercise_id=exercise_id,
                    set_number=nummer,
                    weight_kg=letzte[0],
                    reps=letzte[1],
                    set_type="normal",
                    is_warmup=False,
                    is_completed=False,
                ))

    def _letzte_werte(self, exercise_id: int) -> tuple[float | None, int | None]:
        """Gewicht und Wiederholungen des letzten Arbeitssatzes dieser Uebung."""
        eintrag = self.get_last_weights([exercise_id])[0]
        return eintrag["weight_kg"], eintrag["reps"]

    def plan_targets(self, workout: Workout) -> list[PlanExercise]:
        """Plan-Vorgaben zur Session, leer bei freiem Training."""
        if not workout.plan_day_id:
            return []
        return self.get_plan_day_exercises(workout.plan_day_id)

    def update(self, workout_id: int, data: WorkoutUpdate) -> Workout:
        workout = self.get(workout_id)
        if data.name is not None:
            workout.name = data.name
        if data.finished_at is not None:
            workout.finished_at = data.finished_at
        if data.notes is not None:
            workout.notes = data.notes
        if data.rating is not None:
            workout.rating = data.rating
        return workout

    def finish(self, workout_id: int) -> Workout:
        workout = self.get(workout_id)
        workout.finished_at = datetime.now(timezone.utc)
        return workout

    def delete(self, workout_id: int) -> None:
        workout = self.get(workout_id)
        self.db.delete(workout)

    # --- Sets ---

    def add_set(self, workout_id: int, data: WorkoutSetCreate) -> WorkoutSet:
        self.get(workout_id)  # ensure exists
        exercise = self.db.get(Exercise, data.exercise_id)
        if not exercise:
            raise DomainError("Übung nicht gefunden", {"exercise_id": data.exercise_id})

        # Sync is_warmup and set_type
        set_type = data.set_type
        if data.is_warmup and set_type == "normal":
            set_type = "warmup"
        is_warmup = data.is_warmup or set_type == "warmup"

        ws = WorkoutSet(
            workout_id=workout_id,
            exercise_id=data.exercise_id,
            set_number=data.set_number,
            weight_kg=data.weight_kg,
            reps=data.reps,
            duration_seconds=data.duration_seconds,
            distance_meters=data.distance_meters,
            rpe=data.rpe,
            is_warmup=is_warmup,
            set_type=set_type,
            group_id=data.group_id,
            notes=data.notes,
            is_completed=data.is_completed,
            completed_at=datetime.now(timezone.utc) if data.is_completed else None,
        )
        self.db.add(ws)
        self.db.flush()

        # Check PRs
        self._check_prs(ws)

        return ws

    def update_set(self, set_id: int, data: WorkoutSetUpdate) -> WorkoutSet:
        ws = self.db.get(WorkoutSet, set_id)
        if not ws:
            raise DomainError("Satz nicht gefunden", {"set_id": set_id})
        if data.is_completed is not None and data.is_completed != ws.is_completed:
            ws.is_completed = data.is_completed
            ws.completed_at = datetime.now(timezone.utc) if data.is_completed else None
        for field in ("weight_kg", "reps", "duration_seconds", "distance_meters",
                      "rpe", "is_warmup", "set_type", "group_id", "notes"):
            val = getattr(data, field)
            if val is not None:
                setattr(ws, field, val)

        # Sync is_warmup <-> set_type
        if data.set_type is not None:
            ws.is_warmup = data.set_type == "warmup"
        elif data.is_warmup is not None:
            if data.is_warmup and ws.set_type == "normal":
                ws.set_type = "warmup"
            elif not data.is_warmup and ws.set_type == "warmup":
                ws.set_type = "normal"

        self.db.flush()
        self._check_prs(ws)

        return ws

    def delete_set(self, set_id: int) -> None:
        ws = self.db.get(WorkoutSet, set_id)
        if not ws:
            raise DomainError("Satz nicht gefunden", {"set_id": set_id})
        self.db.delete(ws)

    def get_plan_day_exercises(self, plan_day_id: int) -> list[PlanExercise]:
        return (
            self.db.query(PlanExercise)
            .options(joinedload(PlanExercise.exercise))
            .filter(PlanExercise.plan_day_id == plan_day_id)
            .order_by(PlanExercise.sort_order)
            .all()
        )

    # --- PR checking ---

    def _check_prs(self, ws: WorkoutSet) -> list[PersonalRecord]:
        """Check if a set establishes new personal records."""
        if not ws.is_completed or ws.is_warmup or ws.set_type == "warmup":
            return []

        new_prs: list[PersonalRecord] = []
        weight = ws.weight_kg or 0
        reps = ws.reps or 0
        now = datetime.now(timezone.utc)

        checks: list[tuple[str, float]] = []

        if weight > 0 and reps > 0:
            e1rm = _estimate_1rm(weight, reps)
            checks.append(("1rm", e1rm))
            checks.append(("max_volume", round(weight * reps, 1)))

        if weight > 0:
            checks.append(("max_weight", weight))

        if reps > 0:
            checks.append(("max_reps", float(reps)))

        for pr_type, value in checks:
            existing = (
                self.db.query(PersonalRecord)
                .filter(
                    PersonalRecord.exercise_id == ws.exercise_id,
                    PersonalRecord.pr_type == pr_type,
                )
                .first()
            )
            if existing:
                if value > existing.value:
                    existing.value = value
                    existing.achieved_at = now
                    existing.workout_set_id = ws.id
                    new_prs.append(existing)
            else:
                pr = PersonalRecord(
                    exercise_id=ws.exercise_id,
                    pr_type=pr_type,
                    value=value,
                    achieved_at=now,
                    workout_set_id=ws.id,
                )
                self.db.add(pr)
                new_prs.append(pr)

        return new_prs

    # --- Exercise history ---

    def exercise_history(self, exercise_id: int, limit: int = 5) -> list[dict]:
        """Return last N workout sessions for a given exercise."""
        # Find distinct workout_ids for this exercise, most recent first
        workout_ids = (
            self.db.query(WorkoutSet.workout_id)
            .filter(WorkoutSet.exercise_id == exercise_id, *arbeitssatz())
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .order_by(desc(Workout.started_at))
            .distinct()
            .limit(limit)
            .all()
        )
        workout_ids = [wid for (wid,) in workout_ids]
        if not workout_ids:
            return []

        # Fetch workouts with sets for this exercise
        workouts = (
            self.db.query(Workout)
            .filter(Workout.id.in_(workout_ids))
            .order_by(desc(Workout.started_at))
            .all()
        )

        result = []
        for w in workouts:
            sets = (
                self.db.query(WorkoutSet)
                .options(joinedload(WorkoutSet.exercise))
                .filter(
                    WorkoutSet.workout_id == w.id,
                    WorkoutSet.exercise_id == exercise_id,
                    *arbeitssatz(),
                )
                .order_by(WorkoutSet.set_number)
                .all()
            )
            d = w.started_at
            if isinstance(d, datetime):
                d = d.date()
            result.append({
                "date": d,
                "workout_id": w.id,
                "workout_name": w.name,
                "sets": sets,
            })
        return result

    # --- Suggestions ---

    def get_overload_suggestion(self, exercise_id: int) -> dict:
        """Suggest progressive overload based on last session."""
        history = self.exercise_history(exercise_id, limit=1)
        exercise = self.db.get(Exercise, exercise_id)
        ex_name = exercise.name if exercise else ""

        if not history:
            return {
                "exercise_id": exercise_id,
                "exercise_name": ex_name,
                "reason": "Noch keine Daten vorhanden",
            }

        last_sets = history[0]["sets"]
        working_sets = [
            s for s in last_sets
            if s.is_completed and not s.is_warmup and s.set_type != "warmup"
        ]
        if not working_sets:
            return {
                "exercise_id": exercise_id,
                "exercise_name": ex_name,
                "reason": "Keine Arbeitssätze gefunden",
            }

        last_weight = working_sets[-1].weight_kg
        last_reps = working_sets[-1].reps

        # Check if all sets hit target reps (assume 12 as default max)
        all_hit_target = all(
            (s.reps or 0) >= 12 for s in working_sets
            if s.weight_kg and s.weight_kg == last_weight
        )

        if all_hit_target and last_weight:
            return {
                "exercise_id": exercise_id,
                "exercise_name": ex_name,
                "suggested_weight_kg": round(last_weight + 2.5, 1),
                "suggested_reps": last_reps,
                "last_weight_kg": last_weight,
                "last_reps": last_reps,
                "reason": "Alle Ziel-Reps erreicht → Gewicht erhöhen",
            }
        else:
            return {
                "exercise_id": exercise_id,
                "exercise_name": ex_name,
                "suggested_weight_kg": last_weight,
                "suggested_reps": last_reps,
                "last_weight_kg": last_weight,
                "last_reps": last_reps,
                "reason": "Gleiche Gewichte beibehalten",
            }

    def get_last_weights(self, exercise_ids: list[int]) -> list[dict]:
        """Return last used weight/reps for each exercise."""
        result = []
        for ex_id in exercise_ids:
            last_set = (
                self.db.query(WorkoutSet)
                .join(Workout, WorkoutSet.workout_id == Workout.id)
                .filter(
                    WorkoutSet.exercise_id == ex_id,
                    *arbeitssatz(),
                )
                .order_by(desc(Workout.started_at), desc(WorkoutSet.set_number))
                .first()
            )
            if last_set:
                result.append({
                    "exercise_id": ex_id,
                    "weight_kg": last_set.weight_kg,
                    "reps": last_set.reps,
                    "set_type": last_set.set_type,
                })
            else:
                result.append({
                    "exercise_id": ex_id,
                    "weight_kg": None,
                    "reps": None,
                    "set_type": "normal",
                })
        return result
