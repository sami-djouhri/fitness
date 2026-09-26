"""Benachrichtigungskanal: was der Dienst von sich aus meldet.

``POST /api/anstoss/pruefen`` laeuft ueber ALLE Mandanten und ist damit ein
Verwaltungsvorgang, kein Nutzeraufruf. Er haengt deshalb nicht am
Mandanten-Header, sondern an ``ANSTOSS_TOKEN`` und ist ohne Token gesperrt
(503, wie die Admin-Routen). Das ist nicht Kuer: der Dienst ist ueber den
app-proxy auch von aussen erreichbar.

Der Weg von aussen wurde am 2026-09-12 abgeloest. Vorher fragte ein
Bash-Skript den Dienst per curl ab, hielt Zustand in zwei Dateien und baute
die Nutzlast mit Zeichenkettenersetzung in Python-Quelltext zusammen: ein
Uebungsname mit drei Anfuehrungszeichen fuehrte dort Code aus. Jetzt ruft ein
systemd-Timer nur noch diesen Endpunkt.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.config import settings
from app.db import SessionLocal
from app.mandant_ableiten import alle_mandanten
from app.services import anstoss

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anstoss", tags=["anstoss"])


def _token_pruefen(x_anstoss_token: str | None = Header(None)) -> None:
    if not settings.ANSTOSS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="ANSTOSS_TOKEN ist nicht gesetzt, der Endpunkt ist gesperrt",
        )
    if x_anstoss_token != settings.ANSTOSS_TOKEN:
        raise HTTPException(status_code=401, detail="Token ungültig")


@router.post("/pruefen", dependencies=[Depends(_token_pruefen)])
def pruefen(trockenlauf: bool = Query(False)):
    """Alle Mandanten pruefen und Faelliges melden.

    ``trockenlauf=true`` zeigt, was gesendet wuerde, ohne zu senden und ohne
    das Gedaechtnis fortzuschreiben.
    """
    from app.mqtt import publisher

    mandanten = alle_mandanten()
    ergebnis = {"mandanten": len(mandanten), "meldungen": [], "kanal": publisher.zustand()}

    for sub in mandanten:
        # Eigene Session je Mandant: das Scoping in app/tenant.py liest den
        # Mandanten aus session.info, nicht aus dem Aufruf.
        db = SessionLocal()
        db.info["owner_sub"] = sub
        try:
            meldungen = anstoss.melden(db, sub, trockenlauf=trockenlauf)
            if not trockenlauf:
                db.commit()
            for m in meldungen:
                ergebnis["meldungen"].append({"owner_sub": sub, **m})
        except Exception:
            db.rollback()
            # Ein Mandant mit kaputten Daten darf die uebrigen nicht aufhalten.
            logger.warning("Anstoss fuer einen Mandanten fehlgeschlagen", exc_info=True)
        finally:
            db.close()

    ergebnis["kanal"] = publisher.zustand()
    return ergebnis
