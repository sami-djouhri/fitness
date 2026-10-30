"""Die MealPrep-Kopplung, gegen den echten Adressraum geprueft.

``tests/test_mealprep_adapter.py`` daneben prueft das Verhalten des Moduls
(Nachsicht bei Ausfall, Rueckgabewerte). Es kann nicht auffallen lassen, dass
die Adressen falsch waren, weil es sie selbst vorgibt: gerufen wurde
``/api/profile``, MealPrep hoert auf ``/profile``. Jeder Aufruf waere ein 404
gewesen, und weil das Modul keinen Aufrufer hatte, ist es niemandem
aufgefallen.

Diese Datei pinnt deshalb genau das, was das andere nicht kann:

- die Adressen, wie der laufende MealPrep-Dienst sie meldet,
- den Mandanten-Kopf, ohne den Koerperdaten im falschen Konto landen,
- dass eine gespeicherte Messung die Weitergabe wirklich anstoesst.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from app.services import mealprep_adapter

# Gemessen am laufenden Dienst (openapi.json von mealprep, 2026-09-12).
ADRESSEN = {
    "profil": "/profile",
    "messungen": "/profile/metrics",
    "ziele": "/profile/targets",
}


class _Antwort:
    def __init__(self, daten=None):
        self._daten = daten or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._daten


class _Aufzeichnung:
    """Merkt sich, wohin gerufen wurde und mit welchen Kopfzeilen."""

    def __init__(self, antwort=None):
        self.aufrufe: list[dict] = []
        self._antwort = antwort or _Antwort()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def put(self, url, json=None, headers=None):
        self.aufrufe.append({"methode": "PUT", "url": url, "json": json, "headers": headers or {}})
        return self._antwort

    async def post(self, url, json=None, headers=None):
        self.aufrufe.append({"methode": "POST", "url": url, "json": json, "headers": headers or {}})
        return self._antwort

    async def get(self, url, headers=None):
        self.aufrufe.append({"methode": "GET", "url": url, "headers": headers or {}})
        return self._antwort


@pytest.fixture
def aufzeichnung(monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "http://mealprep:8000")
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_TENANT_SECRET", "")
    aufz = _Aufzeichnung(_Antwort({"kcal": 2400, "protein_g": 180}))
    monkeypatch.setattr(mealprep_adapter.httpx, "AsyncClient", lambda **_: aufz)
    return aufz


@pytest.mark.anyio
async def test_pfade_treffen_den_dienst(aufzeichnung):
    await mealprep_adapter.update_activity_level("moderate", owner_sub="A")
    await mealprep_adapter.sync_body_metric(80.0, owner_sub="A")
    await mealprep_adapter.get_targets(owner_sub="A")

    gerufen = [a["url"] for a in aufzeichnung.aufrufe]
    assert gerufen == [
        f"http://mealprep:8000{ADRESSEN['profil']}",
        f"http://mealprep:8000{ADRESSEN['messungen']}",
        f"http://mealprep:8000{ADRESSEN['ziele']}",
    ]
    assert not any("/api/profile" in u for u in gerufen), \
        "MealPrep montiert den Profil-Router ohne /api"


@pytest.mark.anyio
async def test_mandant_reist_mit(aufzeichnung):
    await mealprep_adapter.sync_body_metric(80.0, owner_sub="MANDANT-A")
    assert aufzeichnung.aufrufe[0]["headers"]["X-Saganta-Sub"] == "MANDANT-A"


@pytest.mark.anyio
async def test_ohne_mandant_kein_header(aufzeichnung):
    """Ein leerer Mandant darf nicht als Kopfzeile gesendet werden: MealPrep
    nimmt dann seinen internen Weg, statt einen leeren Mandanten anzulegen."""
    await mealprep_adapter.sync_body_metric(80.0, owner_sub=None)
    assert "X-Saganta-Sub" not in aufzeichnung.aufrufe[0]["headers"]


@pytest.mark.anyio
async def test_signatur_wenn_geheimnis_gesetzt(aufzeichnung, monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_TENANT_SECRET", "gemeinsames-geheimnis")
    await mealprep_adapter.sync_body_metric(80.0, owner_sub="MANDANT-A")

    erwartet = hmac.new(b"gemeinsames-geheimnis", b"MANDANT-A", hashlib.sha256).hexdigest()
    assert aufzeichnung.aufrufe[0]["headers"]["X-Saganta-Sub-Sig"] == erwartet


@pytest.mark.anyio
async def test_koerperdaten_vollstaendig(aufzeichnung):
    await mealprep_adapter.sync_body_metric(
        80.5, body_fat_pct=18.0, waist_cm=88.0, metric_date="2026-09-12", owner_sub="A",
    )
    gesendet = aufzeichnung.aufrufe[0]["json"]
    assert gesendet == {
        "weight_kg": 80.5, "body_fat_pct": 18.0,
        "waist_cm": 88.0, "metric_date": "2026-09-12",
    }


# --- Der Aufrufer, der vorher fehlte ---

def test_gespeicherte_messung_geht_an_mealprep(client, monkeypatch):
    """Bis 2026-09 hatte der Adapter keinen einzigen Aufrufer."""
    weitergegeben: list[dict] = []

    async def merke(**kwargs):
        weitergegeben.append(kwargs)
        return True

    monkeypatch.setattr(mealprep_adapter, "sync_body_metric", merke)

    r = client.post("/api/body/metrics", json={"date": "2026-09-12", "weight_kg": 80.5})
    assert r.status_code == 201
    assert len(weitergegeben) == 1, "die Messung muss weitergegeben werden"
    assert weitergegeben[0]["weight_kg"] == 80.5
    assert weitergegeben[0]["metric_date"] == "2026-09-12"


def test_ausfall_von_mealprep_blockiert_die_eingabe_nicht(client, monkeypatch):
    async def stirbt(**_):
        raise RuntimeError("MealPrep schlaeft")

    monkeypatch.setattr(mealprep_adapter, "sync_body_metric", stirbt)

    r = client.post("/api/body/metrics", json={"date": "2026-09-12", "weight_kg": 81.0})
    assert r.status_code == 201, "die eigene Erfassung haengt nicht am Nachbardienst"
    assert client.get("/api/body/metrics").json()[0]["weight_kg"] == 81.0


def test_ziele_ohne_mealprep_melden_nicht_verfuegbar(client, monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "")
    daten = client.get("/api/body/mealprep-ziele").json()
    assert daten["verfuegbar"] is False
    assert daten["kcal"] is None, "keine erfundene Null"


def test_ziele_werden_durchgereicht(client, monkeypatch):
    async def ziele(**_):
        return {"kcal": 2400, "protein_g": 180, "carbs_g": 250, "fat_g": 70, "fiber_g": 30}

    monkeypatch.setattr(mealprep_adapter, "get_targets", ziele)
    daten = client.get("/api/body/mealprep-ziele").json()
    assert daten["verfuegbar"] is True
    assert daten["kcal"] == 2400
    assert daten["protein_g"] == 180


def test_zustand_zaehlt_fehlschlaege(client, monkeypatch):
    """Der stille Fallback hat den Pfadfehler jahrelang verdeckt."""
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "http://mealprep:8000")

    class Kaputt:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, *_, **__):
            raise RuntimeError("nicht erreichbar")

    monkeypatch.setattr(mealprep_adapter.httpx, "AsyncClient", lambda **_: Kaputt())
    vorher = mealprep_adapter.zustand()["fehler"]

    r = client.get("/api/body/mealprep-ziele")
    assert r.json()["verfuegbar"] is False

    zustand = mealprep_adapter.zustand()
    assert zustand["fehler"] == vorher + 1
    assert "nicht erreichbar" in zustand["letzter_fehler"]
    assert mealprep_adapter.zustand() == client.get("/health").json()["mealprep"]


# --- Der zweite Weg zum selben Feld (2026-09-18) ---
#
# Der Abgleich hing allein an der Messung. Ein Gewicht laesst sich aber auch
# im Profil aendern, und dieser Weg sagte MealPrep nichts. Gemessen am
# 2026-09-18: Fitness-Profil 82,0 kg (13.09.), MealPrep 80,0 kg (02.03.).


@pytest.mark.anyio
async def test_profil_koerperdaten_gehen_an_das_profil_nicht_an_die_messungen(aufzeichnung):
    """Ein Profilwert hat kein Messdatum und darf keine Messung erfinden."""
    await mealprep_adapter.sync_profil_koerperdaten(weight_kg=82.0, owner_sub="A")

    assert len(aufzeichnung.aufrufe) == 1
    aufruf = aufzeichnung.aufrufe[0]
    assert aufruf["methode"] == "PUT"
    assert aufruf["url"] == f"http://mealprep:8000{ADRESSEN['profil']}"
    assert aufruf["url"] != f"http://mealprep:8000{ADRESSEN['messungen']}"
    assert "metric_date" not in (aufruf["json"] or {})


@pytest.mark.anyio
async def test_nur_gesetzte_felder_reisen_mit(aufzeichnung):
    await mealprep_adapter.sync_profil_koerperdaten(height_cm=180.0, owner_sub="A")
    assert aufzeichnung.aufrufe[0]["json"] == {"height_cm": 180.0}

    await mealprep_adapter.sync_profil_koerperdaten(weight_kg=82.0, height_cm=180.0, owner_sub="A")
    assert aufzeichnung.aufrufe[1]["json"] == {"weight_kg": 82.0, "height_cm": 180.0}


@pytest.mark.anyio
async def test_ohne_werte_kein_aufruf(aufzeichnung):
    """Sonst setzt ein Profil-Update ohne Koerperfelder dort etwas zurueck."""
    assert await mealprep_adapter.sync_profil_koerperdaten(owner_sub="A") is False
    assert aufzeichnung.aufrufe == []


@pytest.mark.anyio
async def test_mandant_reist_auch_hier_mit(aufzeichnung):
    await mealprep_adapter.sync_profil_koerperdaten(weight_kg=82.0, owner_sub="MANDANT-B")
    assert aufzeichnung.aufrufe[0]["headers"]["X-Saganta-Sub"] == "MANDANT-B"


def test_profil_update_stoesst_den_abgleich_an(client, monkeypatch):
    weitergegeben: list[dict] = []

    async def merke(**kwargs):
        weitergegeben.append(kwargs)
        return True

    monkeypatch.setattr(mealprep_adapter, "sync_profil_koerperdaten", merke)

    r = client.put("/api/profil", json={"koerpergewicht_kg": 82.0, "koerpergroesse_cm": 180.0})
    assert r.status_code == 200, r.text
    assert len(weitergegeben) == 1, "die Profil-Aenderung muss weitergegeben werden"
    assert weitergegeben[0]["weight_kg"] == 82.0
    assert weitergegeben[0]["height_cm"] == 180.0


def test_profil_update_ohne_koerperfelder_ruft_nicht(client, monkeypatch):
    """Wer nur seine Geraeteliste aendert, fasst MealPreps Profil nicht an."""
    weitergegeben: list[dict] = []

    async def merke(**kwargs):
        weitergegeben.append(kwargs)
        return True

    monkeypatch.setattr(mealprep_adapter, "sync_profil_koerperdaten", merke)

    r = client.put("/api/profil", json={"erfahrung": "fortgeschritten"})
    assert r.status_code == 200, r.text
    assert weitergegeben == []


def test_ausfall_blockiert_das_profil_speichern_nicht(client, monkeypatch):
    async def stirbt(**_):
        raise RuntimeError("MealPrep schlaeft")

    monkeypatch.setattr(mealprep_adapter, "sync_profil_koerperdaten", stirbt)

    r = client.put("/api/profil", json={"koerpergewicht_kg": 83.5})
    assert r.status_code == 200, "das eigene Profil haengt nicht am Nachbardienst"
    assert client.get("/api/profil").json()["koerpergewicht_kg"] == 83.5
