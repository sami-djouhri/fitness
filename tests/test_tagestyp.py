"""fitness liest den Tagestyp aus dem Kalender.

Nur lesend (Owner-Entscheid 2026-09-13). Der Kalender ist CORE und die eine
Wahrheit darueber, was fuer ein Tag heute ist.

★ Der Kern dieser Tests: der Vorschlag wird **nicht ausgetauscht**. An einem
Feiertag steht weiter derselbe Trainingstag an, er gilt nur nicht als
selbstverstaendlich. Eine App, die den Plan hinter dem Ruecken des Nutzers
umbaut, ist schwerer zu durchschauen als eine, die eine Zeile dazu sagt.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.services import kalender_adapter
from app.services.kalender_adapter import KalenderAdapter
from app.services.progress import ProgressService


class KalenderAttrappe:
    def __init__(self, typ: str | None):
        self._typ = typ
        self.gefragt: list[date] = []

    def tagestyp(self, tag: date) -> str | None:
        self.gefragt.append(tag)
        return self._typ


def _plan_mit_heutigem_tag(client):
    heute = datetime.now(timezone.utc).weekday()
    plan = client.post("/api/plans", json={"name": "PPL", "is_active": True}).json()
    if not plan["is_active"]:
        client.post(f"/api/plans/{plan['id']}/activate")
    client.post(
        f"/api/plans/{plan['id']}/days",
        json={"name": "Legs B", "sort_order": 0, "day_of_week": heute},
    )
    return plan


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def test_ohne_konfiguration_wird_nichts_behauptet():
    """★ ``None`` heisst nicht gemessen, nicht ``frei``.

    Wer beides gleich behandelt, sagt bei jedem Ausfall des Kalenders
    "heute ist frei".
    """
    adapter = KalenderAdapter(base_url="", feed_token="")
    assert adapter.available is False
    assert adapter.tagestyp(date(2026, 12, 25)) is None


def test_ohne_token_gilt_der_dienst_als_unkonfiguriert():
    adapter = KalenderAdapter(base_url="http://kalender:8085", feed_token="")
    assert adapter.available is False


def test_tagestyp_wird_gelesen(monkeypatch):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/day-type"
        assert request.url.params["date"] == "2026-12-25"
        assert request.url.params["token"] == "geheim"
        return httpx.Response(200, json={"type": "feiertag", "name": "1. Weihnachtstag"})

    transport = httpx.MockTransport(handler)
    echt = httpx.Client

    def client_mit_attrappe(*args, **kwargs):
        kwargs["transport"] = transport
        return echt(*args, **kwargs)

    monkeypatch.setattr(kalender_adapter.httpx, "Client", client_mit_attrappe)
    adapter = KalenderAdapter(base_url="http://kalender:8085", feed_token="geheim")

    assert adapter.tagestyp(date(2026, 12, 25)) == "feiertag"


def test_ausfall_meldet_nicht_gemessen(monkeypatch):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("kein Kalender")

    transport = httpx.MockTransport(handler)
    echt = httpx.Client

    def client_mit_attrappe(*args, **kwargs):
        kwargs["transport"] = transport
        return echt(*args, **kwargs)

    monkeypatch.setattr(kalender_adapter.httpx, "Client", client_mit_attrappe)
    adapter = KalenderAdapter(base_url="http://kalender:8085", feed_token="geheim")

    assert adapter.tagestyp(date(2026, 12, 25)) is None


# ---------------------------------------------------------------------------
# Hinweistext
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("typ", ["arbeit", "schule", "frei", None])
def test_normale_tage_bekommen_keinen_hinweis(typ):
    assert kalender_adapter.hinweis(typ, "Legs B") is None


@pytest.mark.parametrize("typ", ["feiertag", "urlaub"])
def test_freie_tage_nennen_den_geplanten_tag(typ):
    text = kalender_adapter.hinweis(typ, "Legs B")
    assert text is not None
    assert "Legs B" in text, "der Plan wird genannt, nicht ersetzt"


def test_ohne_geplanten_tag_bleibt_der_hinweis_verstaendlich():
    text = kalender_adapter.hinweis("urlaub", None)
    assert text is not None
    assert "Legs" not in text


# ---------------------------------------------------------------------------
# Zusammenfassung
# ---------------------------------------------------------------------------


def test_feiertag_macht_den_vorschlag_optional_ohne_ihn_zu_aendern(client, db_session):
    _plan_mit_heutigem_tag(client)
    svc = ProgressService(db_session, kalender=KalenderAttrappe("feiertag"))

    daten = svc.dashboard_summary()

    assert daten.next_plan_day == "Legs B", "der Plan bleibt, was er war"
    assert daten.tagestyp == "feiertag"
    assert daten.vorschlag_optional is True
    assert "Legs B" in daten.tagestyp_hinweis


def test_arbeitstag_aendert_nichts(client, db_session):
    _plan_mit_heutigem_tag(client)
    svc = ProgressService(db_session, kalender=KalenderAttrappe("arbeit"))

    daten = svc.dashboard_summary()

    assert daten.next_plan_day == "Legs B"
    assert daten.tagestyp == "arbeit"
    assert daten.vorschlag_optional is False
    assert daten.tagestyp_hinweis is None


def test_ohne_kalender_sagt_die_app_zum_tag_nichts(client, db_session):
    _plan_mit_heutigem_tag(client)
    svc = ProgressService(db_session, kalender=KalenderAttrappe(None))

    daten = svc.dashboard_summary()

    assert daten.next_plan_day == "Legs B"
    assert daten.tagestyp is None
    assert daten.vorschlag_optional is False
    assert daten.tagestyp_hinweis is None
