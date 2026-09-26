"""Training plan service."""

from sqlalchemy.orm import Session, joinedload

from app.domain import DomainError
from app.models import Plan, PlanDay, PlanExercise, Exercise
from app.schemas import (
    PlanCreate, PlanUpdate, PlanDayCreate, PlanDayUpdate,
    PlanExerciseCreate, PlanExerciseUpdate,
)


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, skip: int = 0, limit: int = 50) -> list[Plan]:
        return self.db.query(Plan).order_by(Plan.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, plan_id: int) -> Plan:
        plan = (
            self.db.query(Plan)
            .options(
                joinedload(Plan.days).joinedload(PlanDay.exercises).joinedload(PlanExercise.exercise)
            )
            .filter(Plan.id == plan_id)
            .first()
        )
        if not plan:
            raise DomainError("Plan nicht gefunden", {"plan_id": plan_id})
        return plan

    def create(self, data: PlanCreate) -> Plan:
        plan = Plan(name=data.name, description=data.description, is_active=data.is_active)
        if data.is_active:
            self._deactivate_all()
        self.db.add(plan)
        return plan

    def update(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get(plan_id)
        if data.name is not None:
            plan.name = data.name
        if data.description is not None:
            plan.description = data.description
        if data.is_active is not None:
            plan.is_active = data.is_active
        return plan

    def delete(self, plan_id: int) -> None:
        plan = self.get(plan_id)
        self.db.delete(plan)

    def activate(self, plan_id: int) -> Plan:
        plan = self.get(plan_id)
        self._deactivate_all()
        plan.is_active = True
        return plan

    def _deactivate_all(self) -> None:
        # Bulk-UPDATE umgeht den do_orm_execute-Tenant-Scope (greift nur bei SELECT)
        # und würde aktive Pläne ALLER Mandanten deaktivieren. Über ein
        # tenant-gescopetes SELECT + Per-Objekt-Update bleibt es beim eigenen sub.
        for plan in self.db.query(Plan).filter(Plan.is_active == True).all():  # noqa: E712
            plan.is_active = False

    # --- Days ---

    def add_day(self, plan_id: int, data: PlanDayCreate) -> PlanDay:
        self.get(plan_id)  # ensure exists
        day = PlanDay(
            plan_id=plan_id,
            name=data.name,
            day_of_week=data.day_of_week,
            sort_order=data.sort_order,
        )
        self.db.add(day)
        return day

    def update_day(self, day_id: int, data: PlanDayUpdate) -> PlanDay:
        day = self.db.get(PlanDay, day_id)
        if not day:
            raise DomainError("Trainingstag nicht gefunden", {"day_id": day_id})
        if data.name is not None:
            day.name = data.name
        if data.day_of_week is not None:
            day.day_of_week = data.day_of_week
        if data.sort_order is not None:
            day.sort_order = data.sort_order
        return day

    def delete_day(self, day_id: int) -> None:
        day = self.db.get(PlanDay, day_id)
        if not day:
            raise DomainError("Trainingstag nicht gefunden", {"day_id": day_id})
        self.db.delete(day)

    # --- Day Exercises ---

    def add_day_exercise(self, day_id: int, data: PlanExerciseCreate) -> PlanExercise:
        day = self.db.get(PlanDay, day_id)
        if not day:
            raise DomainError("Trainingstag nicht gefunden", {"day_id": day_id})
        exercise = self.db.get(Exercise, data.exercise_id)
        if not exercise:
            raise DomainError("Übung nicht gefunden", {"exercise_id": data.exercise_id})
        pe = PlanExercise(
            plan_day_id=day_id,
            exercise_id=data.exercise_id,
            sort_order=data.sort_order,
            target_sets=data.target_sets,
            target_reps_min=data.target_reps_min,
            target_reps_max=data.target_reps_max,
            target_rpe=data.target_rpe,
            rest_seconds=data.rest_seconds,
            notes=data.notes,
        )
        self.db.add(pe)
        return pe

    def update_day_exercise(self, pe_id: int, data: PlanExerciseUpdate) -> PlanExercise:
        pe = self.db.get(PlanExercise, pe_id)
        if not pe:
            raise DomainError("Plan-Übung nicht gefunden", {"id": pe_id})
        for field in ("exercise_id", "sort_order", "target_sets", "target_reps_min",
                      "target_reps_max", "target_rpe", "rest_seconds", "notes"):
            val = getattr(data, field)
            if val is not None:
                setattr(pe, field, val)
        return pe

    def delete_day_exercise(self, pe_id: int) -> None:
        pe = self.db.get(PlanExercise, pe_id)
        if not pe:
            raise DomainError("Plan-Übung nicht gefunden", {"id": pe_id})
        self.db.delete(pe)
