"""Tests for achievement system."""

from datetime import datetime, timezone


def _make_exercise(client, name="Bankdrücken", category="Brust", muscles=None):
    body = {
        "name": name,
        "category": category,
        "equipment": "Langhantel",
        "primary_muscles": muscles or ["Brustmuskel"],
    }
    return client.post("/api/exercises", json=body).json()


def _finish_workout(client, name="Workout"):
    w = client.post("/api/workouts", json={"name": name}).json()
    client.post(f"/api/workouts/{w['id']}/finish")
    return w


def test_list_seeds_definitions(client):
    r = client.get("/api/achievements")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 18, "Expected all seeded achievement definitions"
    assert any(a["key"] == "first_workout" for a in items)
    assert all(a["unlocked_at"] is None for a in items), "Nothing should be unlocked initially"


def test_recent_empty(client):
    r = client.get("/api/achievements/recent")
    assert r.status_code == 200
    assert r.json() == []


def test_check_unlocks_first_workout(client):
    _finish_workout(client)

    r = client.post("/api/achievements/check")
    assert r.status_code == 200
    newly = r.json()
    keys = {a["key"] for a in newly}
    assert "first_workout" in keys

    recent = client.get("/api/achievements/recent").json()
    assert any(a["key"] == "first_workout" for a in recent)


def test_check_is_idempotent(client):
    _finish_workout(client)
    first = client.post("/api/achievements/check").json()
    second = client.post("/api/achievements/check").json()
    assert len(first) >= 1
    assert second == [], "Second check must not re-unlock anything"


def test_workouts_10_milestone(client):
    for i in range(10):
        _finish_workout(client, name=f"W{i}")
    newly = client.post("/api/achievements/check").json()
    keys = {a["key"] for a in newly}
    assert "first_workout" in keys
    assert "workouts_10" in keys
