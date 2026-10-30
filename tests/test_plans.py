"""Tests for training plan API."""


def _create_exercise(client, name="Bankdrücken"):
    r = client.post("/api/exercises", json={
        "name": name, "category": "Brust", "equipment": "Langhantel",
    })
    return r.json()["id"]


def test_create_plan(client):
    r = client.post("/api/plans", json={"name": "PPL", "description": "Push Pull Legs"})
    assert r.status_code == 201
    assert r.json()["name"] == "PPL"


def test_activate_plan(client):
    p1 = client.post("/api/plans", json={"name": "Plan A", "is_active": True}).json()
    p2 = client.post("/api/plans", json={"name": "Plan B"}).json()
    client.post(f"/api/plans/{p2['id']}/activate")

    r1 = client.get(f"/api/plans/{p1['id']}").json()
    r2 = client.get(f"/api/plans/{p2['id']}").json()
    assert r1["is_active"] is False
    assert r2["is_active"] is True


def test_add_day_to_plan(client):
    p = client.post("/api/plans", json={"name": "Test"}).json()
    r = client.post(f"/api/plans/{p['id']}/days", json={"name": "Push", "day_of_week": 0})
    assert r.status_code == 201
    assert r.json()["name"] == "Push"


def test_add_exercise_to_day(client):
    eid = _create_exercise(client)
    p = client.post("/api/plans", json={"name": "Test"}).json()
    d = client.post(f"/api/plans/{p['id']}/days", json={"name": "Push"}).json()
    r = client.post(f"/api/plans/days/{d['id']}/exercises", json={
        "exercise_id": eid,
        "target_sets": 4,
        "target_reps_min": 6,
        "target_reps_max": 8,
        "rest_seconds": 120,
    })
    assert r.status_code == 201
    assert r.json()["target_sets"] == 4


def test_full_plan_structure(client):
    eid = _create_exercise(client)
    p = client.post("/api/plans", json={"name": "Test"}).json()
    d = client.post(f"/api/plans/{p['id']}/days", json={"name": "Push"}).json()
    client.post(f"/api/plans/days/{d['id']}/exercises", json={
        "exercise_id": eid, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 12,
    })
    r = client.get(f"/api/plans/{p['id']}")
    plan = r.json()
    assert len(plan["days"]) == 1
    assert len(plan["days"][0]["exercises"]) == 1
    assert plan["days"][0]["exercises"][0]["exercise_name"] == "Bankdrücken"


def test_delete_plan(client):
    p = client.post("/api/plans", json={"name": "Delete Me"}).json()
    r = client.delete(f"/api/plans/{p['id']}")
    assert r.status_code == 204


def test_delete_day(client):
    p = client.post("/api/plans", json={"name": "Test"}).json()
    d = client.post(f"/api/plans/{p['id']}/days", json={"name": "Push"}).json()
    r = client.delete(f"/api/plans/days/{d['id']}")
    assert r.status_code == 204


def test_update_plan_exercise(client):
    eid = _create_exercise(client)
    p = client.post("/api/plans", json={"name": "Test"}).json()
    d = client.post(f"/api/plans/{p['id']}/days", json={"name": "Push"}).json()
    pe = client.post(f"/api/plans/days/{d['id']}/exercises", json={
        "exercise_id": eid, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 12,
    }).json()
    r = client.put(f"/api/plans/day-exercises/{pe['id']}", json={"target_sets": 5})
    assert r.json()["target_sets"] == 5
