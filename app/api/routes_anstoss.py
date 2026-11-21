"""Benachrichtigungskanal: was der Dienst von sich aus meldet.

``POST /api/anstoss/pruefen`` laeuft ueber ALLE Mandanten und ist damit ein
Verwaltungsvorgang, kein Nutzeraufruf. Er haengt deshalb nicht am
Mandanten-Header, sondern an ``ANSTOSS_TOKEN`` und ist ohne Token gesperrt
(503, wie die Admin-Routen). Das ist nicht Kuer: der Dienst ist ueber den
app-proxy auch von aussen erreichbar.

Der Weg von aussen wurde am 2026-09-12 abgeloest. Vorher fragte ein
Bash-Skript den Dienst per curl ab, hielt Zustand in zwei Dateien und baute
die Nutzlast mit Zeichenkettenersetzung in Python-Quelltext zusammen: ein
Uebungsname mit drei Anfuehrungszeichen fuehrte dort Code aus. Seit dem 2026-11-21
ruft der Timer ``python -m app.anstoss_lauf`` per ``docker exec``: ein Token in
einer Datei am Wirt ist dann ueberfluessig, und der Endpunkt bleibt fuer andere
Wege (gesperrt, solange kein Token gesetzt ist).
"""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.config import settings
from app.services import anstoss

router = APIRouter(prefix="/api/anstoss", tags=["anstoss"])


def _token_pruefen(x_anstoss_token: str | None = Header(None)) -> None:
    if not settings.ANSTOSS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="ANSTOSS_TOKEN ist nicht gesetzt, der Endpunkt ist gesperrt",
        )
    if not hmac.compare_digest((x_anstoss_token or "").encode(), settings.ANSTOSS_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Token ungültig")


@router.post("/pruefen", dependencies=[Depends(_token_pruefen)])
def pruefen(trockenlauf: bool = Query(False)):
    """Alle Mandanten pruefen und Faelliges melden.

    ``trockenlauf=true`` zeigt, was gesendet wuerde, ohne zu senden und ohne
    das Gedaechtnis fortzuschreiben. Der Timer im Haus nimmt diesen Weg nicht
    mehr, sondern ``python -m app.anstoss_lauf`` im Container (kein Token).
    """
    return anstoss.alle_pruefen(trockenlauf=trockenlauf)
