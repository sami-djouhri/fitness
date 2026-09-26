"""Tests for app.services.mealprep_adapter.

The adapter is ~70 LOC of bidirectional HTTP-sync between Fitness and MealPrep.
Before this file existed, errors only surfaced as logger.warning lines: these
tests pin both happy paths and graceful-degradation behaviour so silent regressions
in the sync don't slip through.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import mealprep_adapter


@pytest.fixture(autouse=True)
def _reset_base_url(monkeypatch):
    """Ensure each test starts with a known MEALPREP_BASE_URL value."""
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "http://mealprep.test")
    yield


def _async_client_mock(response_json=None, status_code=200, raise_for_status_error=None):
    """Build a mock httpx.AsyncClient context manager."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = response_json or {}
    if raise_for_status_error is not None:
        response.raise_for_status.side_effect = raise_for_status_error
    else:
        response.raise_for_status.return_value = None

    client_instance = AsyncMock()
    client_instance.put = AsyncMock(return_value=response)
    client_instance.post = AsyncMock(return_value=response)
    client_instance.get = AsyncMock(return_value=response)

    client_cm = MagicMock()
    client_cm.__aenter__ = AsyncMock(return_value=client_instance)
    client_cm.__aexit__ = AsyncMock(return_value=None)
    return client_cm, client_instance


# ---------------------------------------------------------------------------
# Empty base URL → graceful no-op
# ---------------------------------------------------------------------------

def test_update_activity_level_no_base_url(monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "")
    with patch.object(mealprep_adapter.httpx, "AsyncClient") as ac:
        result = asyncio.run(mealprep_adapter.update_activity_level("moderate"))
    assert result is False
    ac.assert_not_called()  # no HTTP attempted


def test_sync_body_metric_no_base_url(monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "")
    with patch.object(mealprep_adapter.httpx, "AsyncClient") as ac:
        result = asyncio.run(mealprep_adapter.sync_body_metric(72.5))
    assert result is False
    ac.assert_not_called()


def test_get_targets_no_base_url(monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "")
    with patch.object(mealprep_adapter.httpx, "AsyncClient") as ac:
        result = asyncio.run(mealprep_adapter.get_targets())
    assert result is None
    ac.assert_not_called()


# ---------------------------------------------------------------------------
# Trailing slash in MEALPREP_BASE_URL is stripped
# ---------------------------------------------------------------------------

def test_trailing_slash_stripped(monkeypatch):
    monkeypatch.setattr(mealprep_adapter.settings, "MEALPREP_BASE_URL", "http://mealprep.test/")
    cm, client = _async_client_mock(status_code=200)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        asyncio.run(mealprep_adapter.update_activity_level("moderate"))
    args, kwargs = client.put.call_args
    # ★ Bis 2026-09 stand hier "/api/profile". Diese Adresse hat es nie
    # gegeben: MealPrep montiert den Profil-Router ohne /api-Vorsatz
    # (am laufenden Dienst gemessen). Der Test hat den Fehler nicht gefunden,
    # sondern festgeschrieben, weil er die Adresse selbst vorgibt und das
    # Modul damals keinen Aufrufer hatte.
    assert args[0] == "http://mealprep.test/profile"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_update_activity_level_success():
    cm, client = _async_client_mock(status_code=200)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        result = asyncio.run(mealprep_adapter.update_activity_level("very_active"))
    assert result is True
    assert client.put.call_args.kwargs["json"] == {"activity_level": "very_active"}


def test_sync_body_metric_weight_only():
    cm, client = _async_client_mock(status_code=201)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        result = asyncio.run(mealprep_adapter.sync_body_metric(75.0))
    assert result is True
    assert client.post.call_args.kwargs["json"] == {"weight_kg": 75.0}


def test_sync_body_metric_with_body_fat():
    cm, client = _async_client_mock(status_code=201)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        result = asyncio.run(mealprep_adapter.sync_body_metric(75.0, body_fat_pct=18.5))
    assert result is True
    assert client.post.call_args.kwargs["json"] == {"weight_kg": 75.0, "body_fat_pct": 18.5}


def test_get_targets_success():
    payload = {"kcal": 2400, "protein_g": 180, "carbs_g": 270, "fat_g": 70}
    cm, _client = _async_client_mock(response_json=payload, status_code=200)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        result = asyncio.run(mealprep_adapter.get_targets())
    assert result == payload


# ---------------------------------------------------------------------------
# Error paths: raise_for_status raises, adapter swallows + logs
# ---------------------------------------------------------------------------

def _http_error(status: int = 500) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://mealprep.test/")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def test_update_activity_level_http_error_returns_false(caplog):
    cm, _client = _async_client_mock(raise_for_status_error=_http_error(500))
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        with caplog.at_level("WARNING"):
            result = asyncio.run(mealprep_adapter.update_activity_level("light"))
    assert result is False
    assert any("Activity-Level" in r.message for r in caplog.records)


def test_sync_body_metric_network_error_returns_false(caplog):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("nope"))
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        with caplog.at_level("WARNING"):
            result = asyncio.run(mealprep_adapter.sync_body_metric(70.0))
    assert result is False
    assert any("Körperdaten" in r.message for r in caplog.records)


def test_get_targets_http_error_returns_none(caplog):
    cm, _client = _async_client_mock(raise_for_status_error=_http_error(404))
    with patch.object(mealprep_adapter.httpx, "AsyncClient", return_value=cm):
        with caplog.at_level("WARNING"):
            result = asyncio.run(mealprep_adapter.get_targets())
    assert result is None
    assert any("Zielwerte" in r.message for r in caplog.records)
