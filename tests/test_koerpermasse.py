"""Koerpermasse (seit 2026-11-07): Anleitung, Messdurchgang, Verlauf, Mandanten."""
from datetime import date

from sqlalchemy import func, select

from app.models import Koerpermass
from app.services import koerpermasse


def test_dreizehn_masse_mit_anleitung_und_echten_umlauten(client):
    r = client.get("/api/body/masse")
    assert r.status_code == 200
    d = r.json()
    assert len(d["definitionen"]) == 13
    assert all(x["anleitung"] for x in d["definitionen"])
    assert next(x for x in d["definitionen"] if x["id"] == "huefte")["name"] == "Hüfte"
    assert "Maßband" in d["allgemein"]
    assert d["aktuell"] == {}


def test_messdurchgang_und_veraenderung(client):
    client.put("/api/body/masse", json={"datum": "2026-10-01", "werte": {"oberarm_r": 33.0, "brust": 98}})
    r = client.put("/api/body/masse", json={"datum": "2026-11-01", "werte": {"oberarm_r": 34.26}})
    assert r.status_code == 200
    a = r.json()["aktuell"]
    assert a["oberarm_r"]["wert_cm"] == 34.3
    assert a["oberarm_r"]["vorher_cm"] == 33.0
    assert a["brust"]["vorher_cm"] is None
    # Derselbe Tag ersetzt statt zu verdoppeln.
    client.put("/api/body/masse", json={"datum": "2026-11-01", "werte": {"oberarm_r": 34.0}})
    v = client.get("/api/body/masse/verlauf", params={"mass": "oberarm_r"}).json()
    assert [(p["datum"], p["wert_cm"]) for p in v] == [("2026-10-01", 33.0), ("2026-11-01", 34.0)]


def test_bauch_aus_altem_gewichtseintrag_fliesst_ein(client):
    client.post("/api/body/metrics", json={"date": "2026-09-01", "weight_kg": 80, "waist_cm": 90})
    client.put("/api/body/masse", json={"datum": "2026-11-01", "werte": {"bauch": 88}})
    b = client.get("/api/body/masse").json()["aktuell"]["bauch"]
    assert (b["wert_cm"], b["vorher_cm"], b["vorher_datum"]) == (88, 90, "2026-09-01")


def test_unbekannt_und_unsinn_abgelehnt(client):
    assert client.put("/api/body/masse", json={"datum": "2026-11-01", "werte": {"ohr": 5}}).status_code == 422
    assert client.put("/api/body/masse", json={"datum": "2026-11-01", "werte": {"wade_l": 2}}).status_code == 422
    assert client.get("/api/body/masse/verlauf", params={"mass": "ohr"}).status_code == 404


def test_masse_sind_mandantengetrennt():
    from tests.test_tenant_isolation import _make_sessionmaker
    Sess = _make_sessionmaker()
    s = Sess()
    s.info["owner_sub"] = "A"
    s.add(Koerpermass(datum=date(2026, 11, 1), mass="brust", wert_cm=99))
    s.commit()
    s.close()
    fremd = Sess()
    fremd.info["owner_sub"] = "B"
    assert fremd.scalar(select(func.count()).select_from(Koerpermass)) == 0
    fremd.close()


def test_reihenfolge_links_vor_rechts():
    ids = [m.id for m in koerpermasse.MASSE]
    for basis in ("oberarm", "unterarm", "oberschenkel", "wade"):
        assert ids.index(f"{basis}_l") + 1 == ids.index(f"{basis}_r")
