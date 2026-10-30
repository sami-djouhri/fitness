"""Tests for workout tracking API."""


def _create_exercise(client, name="Bankdrücken"):
    r = client.post("/api/exercises", json={
        "name": name, "category": "Brust", "equipment": "Langhantel",
    })
    return r.json()["id"]


def test_create_workout(client):
    r = client.post("/api/workouts", json={"name": "Testworkout"})
    assert r.status_code == 201
    assert r.json()["name"] == "Testworkout"
    assert r.json()["finished_at"] is None


def test_add_sets(client):
    eid = _create_exercise(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    r = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid,
        "set_number": 1,
        "weight_kg": 80,
        "reps": 8,
        "rpe": 7.5,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["weight_kg"] == 80
    assert data["reps"] == 8


def test_finish_workout(client):
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    r = client.post(f"/api/workouts/{w['id']}/finish")
    assert r.status_code == 200
    assert r.json()["finished_at"] is not None


def test_update_set(client):
    eid = _create_exercise(client)
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    s = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": eid, "set_number": 1, "weight_kg": 60, "reps": 10,
    }).json()
    r = client.put(f"/api/workouts/sets/{s['id']}", json={"weight_kg": 65, "reps": 8})
    assert r.status_code == 200
    assert r.json()["weight_kg"] == 65


def test_delete_workout(client):
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    r = client.delete(f"/api/workouts/{w['id']}")
    assert r.status_code == 204


def test_list_workouts(client):
    client.post("/api/workouts", json={"name": "W1"})
    client.post("/api/workouts", json={"name": "W2"})
    r = client.get("/api/workouts")
    assert len(r.json()) == 2


def test_workout_with_rating(client):
    w = client.post("/api/workouts", json={"name": "Test"}).json()
    r = client.put(f"/api/workouts/{w['id']}", json={"rating": 4})
    assert r.json()["rating"] == 4
