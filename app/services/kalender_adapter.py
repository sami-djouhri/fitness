"""Anschluss an den Kalender-Dienst (Tagestyp).

Nur lesend, und das ist eine Entscheidung, keine Auslassung
(Entscheid 2026-09-13). Der Kalender ist CORE und die einzige Wahrheit
ueber den Tagestyp; Trainingstage dorthin zu schreiben, solange noch kein
einziges Training erfasst ist, traegt eine Absicht ein, die noch niemand
gelebt hat.

Spiegel von ``mealprep/app/services/kalender_adapter.py``. Bewusst dieselbe
Bauart: zwei Apps, die dieselbe Quelle unterschiedlich befragen, driften
auseinander, und dann streitet man darueber, welcher Tagestyp gilt.

``frei`` als Rueckfall ist hier die sichere Seite: es fuehrt dazu, dass
die App **nichts** Besonderes sagt. Ein Ausfall darf nicht als Feiertag
gelesen werden und einen Trainingstag wegreden.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx

from app.config import settings

log = logging.getLogger(__name__)

#: Tage, an denen ein fester Trainingsplan nicht selbstverstaendlich ist.
FREIE_TAGE = {"feiertag", "urlaub"}

TAGESTYP_LABEL = {
    "feiertag": "Feiertag",
    "urlaub": "Urlaub",
    "schule": "Schultag",
    "arbeit": "Arbeitstag",
    "frei": "frei",
}


class KalenderAdapter:
    def __init__(
        self,
        base_url: str | None = None,
        feed_token: str | None = None,
        timeout: int | None = None,
    ):
        url = base_url if base_url is not None else settings.KALENDER_BASE_URL
        self.base_url = url.rstrip("/") if url else ""
        self.feed_token = (
            feed_token if feed_token is not None else settings.KALENDER_FEED_TOKEN
        )
        self.timeout = timeout or settings.KALENDER_TIMEOUT_SEC

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.feed_token)

    def tagestyp(self, tag: date) -> str | None:
        """Tagestyp fuer ein Datum, oder ``None`` wenn nicht gemessen.

        ⚠️ ``None`` ist nicht ``frei``. Wer beides gleich behandelt, sagt bei
        jedem Ausfall des Kalenders "heute ist frei".
        """
        if not self.available:
            return None
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            ) as c:
                resp = c.get(
                    "/api/day-type",
                    params={"date": tag.isoformat(), "token": self.feed_token},
                )
                resp.raise_for_status()
                return resp.json().get("type")
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Kalender nicht erreichbar (tagestyp %s): %s", tag, exc)
            return None

    def trainingsminuten(self, tag: date) -> int | None:
        """Wie viele Minuten der Kalender fuer Training reserviert hat.

        Bis zum 2026-10-24 fragte diese App den Kalender **nur** nach dem
        Tagestyp, nie nach der Zeit, obwohl ``minuten_quelle: 'kalender'`` im
        Dienst vorgesehen war. Gesetzt hat es nur der Kalender selbst, wenn er
        die Fitness-App aufrief. Wer die App direkt oeffnete, bekam die Vorgabe
        von 45 Minuten, und die Zahl lag die ganze Zeit im Haus.

        ⚠️ ``None`` heisst "nicht gemessen" und ist nicht null Minuten. Es
        deckt drei Faelle ab, die hier gleich behandelt werden duerfen, weil
        die Folge dieselbe ist: kein Kalender angeschlossen, kein
        Trainingsblock an diesem Tag, Kalender nicht erreichbar. In allen
        dreien rechnet die App mit ihrer eigenen Vorgabe und weist sie aus.
        """
        if not self.available:
            return None
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            ) as c:
                resp = c.get(
                    "/api/tagesdecke/trainingszeit",
                    params={"datum": tag.isoformat(), "token": self.feed_token},
                )
                resp.raise_for_status()
                minuten = resp.json().get("minuten")
                return int(minuten) if minuten else None
        except (httpx.HTTPError, Exception) as exc:
            log.warning("Kalender nicht erreichbar (trainingszeit %s): %s", tag, exc)
            return None


def hinweis(tagestyp: str | None, trainingstag_name: str | None) -> str | None:
    """Was die App zum Tagestyp sagt, wenn ueberhaupt etwas.

    Der Vorschlag wird **nicht ausgetauscht**. An einem Feiertag steht
    weiter derselbe Trainingstag an; er wird nur als nicht selbstverstaendlich
    ausgewiesen. Eine App, die den Plan hinter dem Ruecken des Nutzers
    umbaut, ist schwerer zu durchschauen als eine, die eine Zeile dazu sagt.
    """
    if tagestyp is None or tagestyp not in FREIE_TAGE:
        return None
    label = TAGESTYP_LABEL.get(tagestyp, tagestyp)
    if trainingstag_name:
        return (
            f"{label}. Nach Plan waere '{trainingstag_name}' dran, "
            "das muss heute aber nicht sein."
        )
    return f"{label}. Heute muss kein Training sein."
