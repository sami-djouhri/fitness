"""Kopplung an MealPrep.

★ Zwei Dinge waren hier bis 2026-09 falsch, und beide blieben unbemerkt, weil
das Modul **keinen einzigen Aufrufer** hatte. Die elf Tests daneben waren
gruen, weil sie die Adresse selbst vorgeben.

1. **Die Pfade zeigten ins Leere.** Gerufen wurde ``/api/profile``,
   ``/api/profile/metrics`` und ``/api/profile/targets``. MealPrep montiert
   diesen Router ohne ``/api``, er hoert auf ``/profile`` (gemessen am
   laufenden Dienst ueber dessen openapi.json). Jeder Aufruf waere auf einen
   404 gelaufen.
2. **Der Mandant fehlte.** MealPrep leitet ihn aus ``X-Saganta-Sub`` ab. Ohne
   den Header gilt der interne Weg, und die Koerperdaten des einen Nutzers
   waeren im Konto eines anderen gelandet. In einem Mehrpersonen-Betrieb ist
   das der schlimmere der beiden Fehler.

Die Nachsicht des Moduls ("graceful degradation") hat den ersten Fehler
verdeckt: ein fehlgeschlagener Aufruf schreibt eine Zeile ins Protokoll und
gibt False zurueck, und niemand liest mit. Deshalb zaehlen die Funktionen
ihre Fehlschlaege jetzt mit, und ``letzter_fehler`` steht im Zustandsbericht
des Dienstes.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0

# Beobachtbarkeit statt stiller Nachsicht: wer wissen will, ob die Kopplung
# traegt, liest /health (app/main.py).
_zaehler = {"versuche": 0, "fehler": 0}
_letzter_fehler: str | None = None


def zustand() -> dict:
    """Zaehlstand der Kopplung fuer den Zustandsbericht."""
    return {
        "konfiguriert": bool(_base_url()),
        "versuche": _zaehler["versuche"],
        "fehler": _zaehler["fehler"],
        "letzter_fehler": _letzter_fehler,
    }


def _merken(fehler: str | None) -> None:
    global _letzter_fehler
    _zaehler["versuche"] += 1
    if fehler:
        _zaehler["fehler"] += 1
        _letzter_fehler = fehler


def _base_url() -> str | None:
    url = settings.MEALPREP_BASE_URL.rstrip("/") if settings.MEALPREP_BASE_URL else ""
    return url or None


def _kopfzeilen(owner_sub: str | None) -> dict[str, str]:
    """Mandanten-Kopfzeilen fuer den Aufruf von Dienst zu Dienst.

    Die Signatur haengt an einem Geheimnis, das MealPrep kennt. Fehlt sie,
    nimmt MealPrep den Header in der Beobachtungsphase noch an und schreibt
    eine Warnung; schaltet MealPrep scharf, braucht es
    ``MEALPREP_TENANT_SECRET``.
    """
    if not owner_sub:
        return {}
    kopf = {"X-Saganta-Sub": owner_sub}
    geheimnis = settings.MEALPREP_TENANT_SECRET
    if geheimnis:
        import hashlib
        import hmac
        kopf["X-Saganta-Sub-Sig"] = hmac.new(
            geheimnis.encode(), owner_sub.encode(), hashlib.sha256
        ).hexdigest()
    return kopf


async def sync_profil_koerperdaten(
    weight_kg: float | None = None,
    height_cm: float | None = None,
    owner_sub: str | None = None,
) -> bool:
    """Gewicht und Groesse aus dem Profil ins MealPrep-Profil schreiben.

    ★ Warum das neben ``sync_body_metric`` noetig ist: der Abgleich hing bis
    zum 2026-09-18 allein an ``POST /api/body/metrics``, also am Erfassen
    einer **Messung**. Wer sein Gewicht im **Profil** korrigiert, loeste
    nichts aus. Beide Wege fuehren fuer den Nutzer sichtbar zum selben Feld,
    nur einer von ihnen sagte es dem Nachbardienst. Gemessen am 2026-09-18:
    Fitness-Profil 82,0 kg vom 13.09., MealPrep 80,0 kg vom 02.03. MealPrep
    rechnete seinen Grundumsatz also 199 Tage lang auf einem Wert, den der
    Nutzer in der anderen App schon berichtigt hatte.

    Bewusst ``PUT /profile`` und nicht ``POST /profile/metrics``: ein
    Profilwert hat kein Messdatum. Eine Messung mit dem heutigen Datum
    anzulegen waere eine Behauptung ueber einen Tag, an dem niemand auf der
    Waage stand, und sie wuerde in der Verlaufskurve als echter Punkt
    erscheinen.

    Gibt False zurueck, wenn nichts zu schicken war oder MealPrep nicht
    erreichbar ist. Der Aufrufer darf daran nicht haengen.
    """
    base = _base_url()
    if not base:
        return False
    nutzlast: dict = {}
    if weight_kg is not None:
        nutzlast["weight_kg"] = weight_kg
    if height_cm is not None:
        nutzlast["height_cm"] = height_cm
    if not nutzlast:
        return False
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.put(
                f"{base}/profile",
                json=nutzlast,
                headers=_kopfzeilen(owner_sub),
            )
            r.raise_for_status()
            _merken(None)
            return True
    except Exception as fehler:
        _merken(f"profil_koerperdaten: {fehler}")
        logger.warning("MealPrep: Konnte Profil-Koerperdaten nicht abgleichen", exc_info=True)
        return False


async def update_activity_level(level: str, owner_sub: str | None = None) -> bool:
    """Aktivitaetsniveau ins MealPrep-Profil schreiben."""
    base = _base_url()
    if not base:
        return False
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.put(
                f"{base}/profile",
                json={"activity_level": level},
                headers=_kopfzeilen(owner_sub),
            )
            r.raise_for_status()
            _merken(None)
            return True
    except Exception as fehler:
        _merken(f"activity_level: {fehler}")
        logger.warning("MealPrep: Konnte Activity-Level nicht aktualisieren", exc_info=True)
        return False


async def sync_body_metric(
    weight_kg: float,
    body_fat_pct: float | None = None,
    waist_cm: float | None = None,
    metric_date: str | None = None,
    owner_sub: str | None = None,
) -> bool:
    """Koerpermessung nach MealPrep weitergeben.

    MealPrep rechnet daraus Grundumsatz und Kalorienziel. Ohne diesen Weg
    musste man sein Gewicht in beiden Apps eintragen.
    """
    base = _base_url()
    if not base:
        return False
    try:
        payload: dict = {"weight_kg": weight_kg}
        if body_fat_pct is not None:
            payload["body_fat_pct"] = body_fat_pct
        if waist_cm is not None:
            payload["waist_cm"] = waist_cm
        if metric_date is not None:
            payload["metric_date"] = metric_date
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{base}/profile/metrics",
                json=payload,
                headers=_kopfzeilen(owner_sub),
            )
            r.raise_for_status()
            _merken(None)
            return True
    except Exception as fehler:
        _merken(f"body_metric: {fehler}")
        logger.warning("MealPrep: Konnte Körperdaten nicht synchronisieren", exc_info=True)
        return False


async def get_targets(owner_sub: str | None = None) -> dict | None:
    """Kalorien- und Makroziele aus MealPrep holen."""
    base = _base_url()
    if not base:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{base}/profile/targets",
                headers=_kopfzeilen(owner_sub),
            )
            r.raise_for_status()
            _merken(None)
            return r.json()
    except Exception as fehler:
        _merken(f"targets: {fehler}")
        logger.warning("MealPrep: Konnte Zielwerte nicht abrufen", exc_info=True)
        return None
