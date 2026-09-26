"""Multi-Tenant-Scoping auf ORM-Ebene (fail-closed): analog lager.

do_orm_execute haengt an jede SELECT gegen ein Tenant-Modell
``owner_sub == <session-sub>`` an; before_flush stempelt neue Objekte.
exercise + achievement sind GETEILTE Referenzkataloge (global, kein Scoping).
sub steht in session.info["owner_sub"] (get_db, Fallback DEFAULT_OWNER_SUB).
"""

from sqlalchemy import event
from sqlalchemy.orm import with_loader_criteria

from app.config import settings
from app.db import SessionLocal
from app.models import (
    AnstossMerker,
    BodyMetric,
    ExerciseSelection,
    Nutzerprofil,
    PersonalRecord,
    Plan,
    PlanDay,
    PlanExercise,
    Tagesschritte,
    UserAchievement,
    Workout,
    WorkoutSet,
)

# NICHT dabei: Exercise, Achievement = geteilte Kataloge. Was an einem
# geteilten Katalog einer einzelnen Person gehoert, braucht eine eigene
# Tabelle: die Uebungsauswahl sass bis 2026-09 als Spalte am Katalog und
# galt damit fuer alle Mandanten zugleich (``ExerciseSelection``).
TENANT_MODELS = (
    Plan,
    PlanDay,
    PlanExercise,
    Workout,
    WorkoutSet,
    BodyMetric,
    PersonalRecord,
    UserAchievement,
    ExerciseSelection,
    AnstossMerker,
    Nutzerprofil,
    Tagesschritte,
)


def _session_sub(session) -> str:
    return session.info.get("owner_sub") or settings.DEFAULT_OWNER_SUB


@event.listens_for(SessionLocal, "do_orm_execute")
def _apply_tenant_scope(execute_state) -> None:
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get("skip_tenant"):
        return
    sub = _session_sub(execute_state.session)
    for model in TENANT_MODELS:
        # Kriterium als Lambda: with_loader_criteria cached das SQL-Kriterium stark;
        # ein nicht-Lambda mit variablem Wert backt den ERSTEN sub (Seed/Start =
        # DEFAULT_OWNER_SUB) in den Statement-Cache und wiederverwendet ihn fuer ALLE
        # folgenden Requests → Cross-Tenant-Datenleck. Lambda => sub als variabler
        # Closure-Bindparam (SQLAlchemy-Doku-Pattern).
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(model, lambda cls: cls.owner_sub == sub, include_aliases=True)
        )


@event.listens_for(SessionLocal, "before_flush")
def _stamp_tenant(session, _flush_context, _instances) -> None:
    sub = _session_sub(session)
    for obj in session.new:
        if isinstance(obj, TENANT_MODELS) and not getattr(obj, "owner_sub", None):
            obj.owner_sub = sub
