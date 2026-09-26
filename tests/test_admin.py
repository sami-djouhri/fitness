"""Tests for admin backup-export endpoint.

★ Diese Datei war vom 14.07.2026 bis zum 05.09.2026 rot, alle zwoelf Tests.
An dem Tag bekamen die Admin-Routen ihre fail-closed-Sperre (Audit F1,
``routes_admin.require_admin``, Commit c56aa7c); die Tests stammen vom 04.07.
und riefen weiter ohne ``X-Admin-Token`` auf. Danach konnten sie in keinem
Zustand gruen sein: ohne konfigurierten Token 503, mit Token und ohne Header
401. Aufgefallen ist es erst, als fitness ein ``run-tests.sh`` bekam. Vorher
hat den Lauf schlicht niemand gestartet.

Die Fixture unten setzt den Token und schickt ihn mit. Die Sperre selbst wird
jetzt ausdruecklich geprueft (``TestAdminSperre``), denn genau das fehlte: der
Schutz war da, die Pruefung dafuer nicht.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.config import settings
from app.models import (
    Achievement,
    BodyMetric,
    Exercise,
    Plan,
    PlanDay,
    Workout,
    WorkoutSet,
)


ADMIN_TOKEN = "pruflauf-admin-token"


@pytest.fixture(autouse=True)
def _admin_gate(monkeypatch, client):
    """Admin-Sperre fuer diese Datei konfigurieren und den Token mitschicken.

    Autouse, damit nicht neunzehn Aufrufstellen einzeln nachgezogen werden
    muessen. Die Sperre selbst wird in TestAdminSperre bewusst OHNE diese
    Fixture-Wirkung geprueft, indem der Header dort wieder entfernt wird.
    """
    monkeypatch.setattr(settings, "ADMIN_TOKEN", ADMIN_TOKEN)
    client.headers.update({"X-Admin-Token": ADMIN_TOKEN})


class TestAdminSperre:
    """Die Sperre, die seit dem 14.07.2026 da ist und nie geprueft wurde."""

    def test_ohne_token_header_401(self, client):
        client.headers.pop("X-Admin-Token", None)
        assert client.get("/api/admin/export").status_code == 401

    def test_falscher_token_401(self, client):
        client.headers.update({"X-Admin-Token": "falsch"})
        assert client.get("/api/admin/export").status_code == 401

    def test_ohne_konfigurierten_token_503(self, client, monkeypatch):
        """Fail-closed: nicht konfiguriert heisst gesperrt, nicht offen."""
        monkeypatch.setattr(settings, "ADMIN_TOKEN", "")
        assert client.get("/api/admin/export").status_code == 503


def _seed(db):
    """Seed a small, FK-consistent fixture across most tables."""
    ex = Exercise(name="Bench Press", category="strength", equipment="barbell")
    db.add(ex)
    db.flush()

    plan = Plan(name="PPL", description="Push / Pull / Legs", is_active=True)
    db.add(plan)
    db.flush()

    day = PlanDay(plan_id=plan.id, name="Push", day_of_week=1, sort_order=0)
    db.add(day)
    db.flush()

    workout = Workout(
        plan_day_id=day.id,
        name="Push A",
        started_at=datetime(2026, 6, 11, 17, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 6, 11, 18, 30, tzinfo=timezone.utc),
        rating=4,
    )
    db.add(workout)
    db.flush()

    db.add(WorkoutSet(
        workout_id=workout.id,
        exercise_id=ex.id,
        set_number=1,
        weight_kg=80.0,
        reps=8,
        rpe=8.0,
    ))

    db.add(BodyMetric(date=date(2026, 6, 10), weight_kg=82.4, body_fat_pct=18.0))
    db.add(Achievement(key="first_workout", name="Erstes Workout", icon="🏋️"))
    db.commit()


# ---------------------------------------------------------------------------
# /api/admin/export
# ---------------------------------------------------------------------------

def test_export_empty_db_has_all_tables(client):
    r = client.get("/api/admin/export")
    assert r.status_code == 200
    payload = r.json()
    assert payload["schema_version"] == 1
    assert "exported_at" in payload
    assert "row_counts" in payload
    # Every model registered should appear, even empty
    expected_tables = {
        "exercise", "plan", "plan_day", "plan_exercise",
        "workout", "workout_set",
        "body_metric", "personal_record",
        "achievement", "user_achievement",
    }
    assert expected_tables == set(payload["tables"].keys())
    assert all(v == 0 for v in payload["row_counts"].values())


def test_export_seeded_db_has_rows(client, db_session):
    _seed(db_session)
    r = client.get("/api/admin/export")
    assert r.status_code == 200
    payload = r.json()

    assert payload["row_counts"]["exercise"] == 1
    assert payload["row_counts"]["plan"] == 1
    assert payload["row_counts"]["plan_day"] == 1
    assert payload["row_counts"]["workout"] == 1
    assert payload["row_counts"]["workout_set"] == 1
    assert payload["row_counts"]["body_metric"] == 1
    assert payload["row_counts"]["achievement"] == 1
    # tables with no rows in seed
    assert payload["row_counts"]["plan_exercise"] == 0
    assert payload["row_counts"]["personal_record"] == 0
    assert payload["row_counts"]["user_achievement"] == 0


def test_export_preserves_ids_and_fks(client, db_session):
    _seed(db_session)
    payload = client.get("/api/admin/export").json()

    ex_row = payload["tables"]["exercise"][0]
    plan_row = payload["tables"]["plan"][0]
    day_row = payload["tables"]["plan_day"][0]
    workout_row = payload["tables"]["workout"][0]
    set_row = payload["tables"]["workout_set"][0]

    # PKs are stable integers
    assert isinstance(ex_row["id"], int) and ex_row["id"] > 0
    # FKs match parent PKs
    assert day_row["plan_id"] == plan_row["id"]
    assert workout_row["plan_day_id"] == day_row["id"]
    assert set_row["workout_id"] == workout_row["id"]
    assert set_row["exercise_id"] == ex_row["id"]


def test_export_serializes_dates_as_iso_strings(client, db_session):
    _seed(db_session)
    payload = client.get("/api/admin/export").json()

    body_row = payload["tables"]["body_metric"][0]
    assert body_row["date"] == "2026-06-10"

    workout_row = payload["tables"]["workout"][0]
    # ISO 8601 with timezone
    assert workout_row["started_at"].startswith("2026-06-11T17:00:00")
    assert "+00:00" in workout_row["started_at"] or workout_row["started_at"].endswith("Z")


def test_export_has_attachment_content_disposition(client):
    r = client.get("/api/admin/export")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "fitness-backup.json" in cd


# ---------------------------------------------------------------------------
# /api/admin/import
# ---------------------------------------------------------------------------

CONFIRM = "I_UNDERSTAND_THIS_REPLACES_ALL_DATA"


def test_import_missing_confirm_returns_400(client):
    payload = client.get("/api/admin/export").json()
    r = client.post("/api/admin/import", json=payload)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "missing_or_invalid_confirm_token"


def test_import_wrong_confirm_returns_400(client):
    payload = client.get("/api/admin/export").json()
    r = client.post("/api/admin/import?confirm=wrong-token", json=payload)
    assert r.status_code == 400


def test_import_dry_run_does_not_mutate(client, db_session):
    _seed(db_session)
    payload_full = client.get("/api/admin/export").json()
    # Erase the seeded workout from payload to confirm dry-run does NOT delete it
    payload_full["tables"]["workout"] = []
    payload_full["tables"]["workout_set"] = []

    r = client.post("/api/admin/import?dry_run=true", json=payload_full)
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True
    assert body["compatible"] is True

    # Original data still present
    again = client.get("/api/admin/export").json()
    assert again["row_counts"]["workout"] == 1
    assert again["row_counts"]["workout_set"] == 1


def test_import_incompatible_schema_returns_400(client):
    bad = {"schema_version": 999, "tables": {}}
    r = client.post(f"/api/admin/import?confirm={CONFIRM}", json=bad)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "incompatible_schema_version"
    assert detail["expected_schema_version"] == 1


def test_import_malformed_payload_returns_400(client):
    r = client.post(f"/api/admin/import?confirm={CONFIRM}", json={"no_tables_here": True})
    assert r.status_code == 400


def test_import_roundtrip_preserves_data(client, db_session):
    _seed(db_session)
    snapshot = client.get("/api/admin/export").json()

    r = client.post(f"/api/admin/import?confirm={CONFIRM}", json=snapshot)
    assert r.status_code == 200
    result = r.json()
    assert result["dry_run"] is False
    assert result["inserted"]["workout"] == 1
    assert result["inserted"]["exercise"] == 1

    # Re-export and compare
    after = client.get("/api/admin/export").json()
    assert after["row_counts"] == snapshot["row_counts"]


def test_import_replaces_existing_data(client, db_session):
    _seed(db_session)
    # Build a payload with DIFFERENT data than what's seeded
    from datetime import datetime, timezone
    payload = {
        "schema_version": 1,
        "tables": {
            "exercise": [
                {"id": 99, "name": "Squat", "category": "strength", "equipment": "barbell",
                 "primary_muscles_json": None, "secondary_muscles_json": None,
                 "is_compound": True, "is_selected": True, "notes": None,
                 "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()},
            ],
            "plan": [], "plan_day": [], "plan_exercise": [],
            "workout": [], "workout_set": [],
            "body_metric": [], "personal_record": [],
            "achievement": [], "user_achievement": [],
        },
    }

    r = client.post(f"/api/admin/import?confirm={CONFIRM}", json=payload)
    assert r.status_code == 200
    result = r.json()
    # The seeded workout was deleted (cascade via reversed FK order)
    assert result["deleted"]["workout"] == 1
    assert result["inserted"]["exercise"] == 1

    # New data only
    after = client.get("/api/admin/export").json()
    assert after["row_counts"]["exercise"] == 1
    assert after["row_counts"]["workout"] == 0
    assert after["tables"]["exercise"][0]["name"] == "Squat"
