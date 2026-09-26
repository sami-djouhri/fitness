"""Tests for body metrics API."""

from datetime import date, timedelta


def _payload(d: date, weight: float = 80.0, **kwargs):
    return {"date": d.isoformat(), "weight_kg": weight, **kwargs}


def test_create_and_list(client):
    today = date.today()
    r = client.post("/api/body/metrics", json=_payload(today, 80.5))
    assert r.status_code == 201
    assert r.json()["weight_kg"] == 80.5

    r = client.get("/api/body/metrics")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_same_date_replaces(client):
    today = date.today()
    client.post("/api/body/metrics", json=_payload(today, 80.0))
    r = client.post("/api/body/metrics", json=_payload(today, 79.5, body_fat_pct=18.0))
    assert r.status_code == 201
    assert r.json()["weight_kg"] == 79.5
    assert r.json()["body_fat_pct"] == 18.0

    listing = client.get("/api/body/metrics").json()
    assert len(listing) == 1, "Same-date entry must update, not duplicate"


def test_delete(client):
    today = date.today()
    created = client.post("/api/body/metrics", json=_payload(today)).json()
    r = client.delete(f"/api/body/metrics/{created['id']}")
    assert r.status_code == 204
    assert client.get("/api/body/metrics").json() == []


def test_delete_unknown(client):
    r = client.delete("/api/body/metrics/9999")
    assert r.status_code == 422


def test_trend_empty(client):
    r = client.get("/api/body/trend?days=30")
    assert r.status_code == 200
    assert r.json() == []


def test_trend_moving_average(client):
    today = date.today()
    weights = [80.0, 81.0, 80.0, 79.5, 80.5]
    for offset, w in enumerate(weights):
        client.post("/api/body/metrics", json=_payload(today - timedelta(days=4 - offset), w))

    trend = client.get("/api/body/trend?days=30").json()
    assert len(trend) == 5
    assert trend[0]["weight_kg"] == 80.0
    assert trend[0]["moving_avg"] == 80.0
    avg_last = round(sum(weights) / len(weights), 2)
    assert trend[-1]["moving_avg"] == avg_last
