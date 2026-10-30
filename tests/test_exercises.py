"""Tests for exercise catalog API."""


def test_create_exercise(client):
    r = client.post("/api/exercises", json={
        "name": "Bankdrücken",
        "category": "Brust",
        "equipment": "Langhantel",
        "primary_muscles": ["Brust", "Trizeps"],
        "is_compound": True,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Bankdrücken"
    assert data["category"] == "Brust"
    assert data["is_compound"] is True
    assert "Brust" in data["primary_muscles"]


def test_list_exercises(client):
    client.post("/api/exercises", json={"name": "Übung A", "category": "Brust", "equipment": "Langhantel"})
    client.post("/api/exercises", json={"name": "Übung B", "category": "Rücken", "equipment": "Kabelzug"})
    r = client.get("/api/exercises")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_filter_by_category(client):
    client.post("/api/exercises", json={"name": "Übung A", "category": "Brust", "equipment": "Langhantel"})
    client.post("/api/exercises", json={"name": "Übung B", "category": "Rücken", "equipment": "Kabelzug"})
    r = client.get("/api/exercises?category=Brust")
    assert len(r.json()) == 1
    assert r.json()[0]["category"] == "Brust"


def test_update_exercise(client):
    r = client.post("/api/exercises", json={"name": "Test", "category": "Core", "equipment": "Körpergewicht"})
    eid = r.json()["id"]
    r2 = client.put(f"/api/exercises/{eid}", json={"name": "Test Updated"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "Test Updated"


def test_delete_exercise(client):
    r = client.post("/api/exercises", json={"name": "Delete Me", "category": "Core", "equipment": "Körpergewicht"})
    eid = r.json()["id"]
    r2 = client.delete(f"/api/exercises/{eid}")
    assert r2.status_code == 204
    r3 = client.get(f"/api/exercises/{eid}")
    assert r3.status_code == 422


def test_duplicate_name_rejected(client):
    client.post("/api/exercises", json={"name": "Unique", "category": "Core", "equipment": "Körpergewicht"})
    r = client.post("/api/exercises", json={"name": "Unique", "category": "Core", "equipment": "Körpergewicht"})
    assert r.status_code == 422


def test_search_exercises(client):
    client.post("/api/exercises", json={"name": "Bankdrücken", "category": "Brust", "equipment": "Langhantel"})
    client.post("/api/exercises", json={"name": "Kniebeugen", "category": "Beine", "equipment": "Langhantel"})
    r = client.get("/api/exercises?search=Bank")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Bankdrücken"
