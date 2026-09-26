"""Admin service: backup-export and restore-import of all tables.

Export is a single-tenant full snapshot: primary keys preserved so a round-trip
restore reconstructs FKs. Import is destructive (truncates all tables before
inserting) and gated behind an explicit confirm token at the route layer.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    BodyMetric,
    Exercise,
    PersonalRecord,
    Plan,
    PlanDay,
    PlanExercise,
    UserAchievement,
    Workout,
    WorkoutSet,
)

EXPORT_SCHEMA_VERSION = 1
IMPORT_CONFIRM_TOKEN = "I_UNDERSTAND_THIS_REPLACES_ALL_DATA"


def _serialize(value: Any) -> Any:
    """Convert ORM column values into JSON-safe primitives."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


# Order matters for round-trip imports: parents before children, so FK targets exist.
_EXPORT_ORDER: list[type] = [
    Exercise,
    Plan,
    PlanDay,
    PlanExercise,
    Workout,
    WorkoutSet,
    BodyMetric,
    PersonalRecord,
    Achievement,
    UserAchievement,
]


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        col.name: _serialize(getattr(row, col.name))
        for col in row.__table__.columns
    }


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def export_all(self) -> dict[str, Any]:
        """Snapshot every row of every table into one JSON-serializable dict."""
        tables: dict[str, list[dict[str, Any]]] = {}
        for model in _EXPORT_ORDER:
            rows = self.db.query(model).order_by(model.id.asc()).all()
            tables[model.__tablename__] = [_row_to_dict(r) for r in rows]

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": EXPORT_SCHEMA_VERSION,
            "row_counts": {name: len(rows) for name, rows in tables.items()},
            "tables": tables,
        }

    # ------------------------------------------------------------------
    # Import (destructive)
    # ------------------------------------------------------------------

    def validate_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check structure + schema_version without mutating anything.

        Returns a manifest: {`row_counts`, `unknown_tables`, `schema_version`,
        `compatible`}. Raises `ValueError` for hard structural problems.
        """
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
        if "tables" not in payload or not isinstance(payload["tables"], dict):
            raise ValueError("payload missing 'tables' object")

        schema_version = payload.get("schema_version")
        if schema_version != EXPORT_SCHEMA_VERSION:
            return {
                "compatible": False,
                "schema_version": schema_version,
                "expected_schema_version": EXPORT_SCHEMA_VERSION,
                "row_counts": {},
                "unknown_tables": [],
            }

        known = {m.__tablename__ for m in _EXPORT_ORDER}
        tables = payload["tables"]
        unknown = [name for name in tables if name not in known]

        row_counts = {name: len(rows) for name, rows in tables.items() if isinstance(rows, list)}
        return {
            "compatible": True,
            "schema_version": schema_version,
            "row_counts": row_counts,
            "unknown_tables": unknown,
        }

    def import_all(self, payload: dict[str, Any]) -> dict[str, Any]:
        """**DESTRUCTIVE**: truncate every table, then re-insert rows from payload.

        All-or-nothing: wraps everything in a single transaction; on any error
        the DB rolls back to its pre-import state. Inserts in `_EXPORT_ORDER`
        (parents first) so FKs resolve.
        """
        manifest = self.validate_import(payload)
        if not manifest["compatible"]:
            raise ValueError(
                f"schema_version {manifest['schema_version']} != "
                f"expected {EXPORT_SCHEMA_VERSION}"
            )

        tables = payload["tables"]
        deleted_counts: dict[str, int] = {}
        inserted_counts: dict[str, int] = {}

        try:
            # Truncate children-first (reverse FK order) to avoid IntegrityError
            for model in reversed(_EXPORT_ORDER):
                deleted_counts[model.__tablename__] = self.db.query(model).delete()
            self.db.flush()

            # Insert parents-first
            for model in _EXPORT_ORDER:
                rows = tables.get(model.__tablename__, []) or []
                for raw in rows:
                    obj = model(**_deserialize_row(model, raw))
                    self.db.add(obj)
                inserted_counts[model.__tablename__] = len(rows)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "deleted": deleted_counts,
            "inserted": inserted_counts,
            "schema_version": manifest["schema_version"],
        }


def _deserialize_row(model: type, raw: dict[str, Any]) -> dict[str, Any]:
    """Reverse `_row_to_dict`: parse ISO strings back into date/datetime as needed."""
    out: dict[str, Any] = {}
    columns = {col.name: col for col in model.__table__.columns}
    for key, value in raw.items():
        col = columns.get(key)
        if col is None:
            continue  # ignore unknown columns (forwards-compat)
        out[key] = _coerce(value, col.type)
    return out


def _coerce(value: Any, sql_type: Any) -> Any:
    """Re-hydrate JSON primitives into the python types SQLAlchemy expects."""
    if value is None:
        return None
    type_name = type(sql_type).__name__
    if type_name == "DateTime" and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if type_name == "Date" and isinstance(value, str):
        return date.fromisoformat(value)
    return value
