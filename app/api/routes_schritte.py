"""Tagesschritte vom Handy.

Die native App liest sie aus Health Connect und traegt sie nach, sobald sie
das Heimnetz erreicht. Nach aussen ist dieser Dienst nicht erreichbar, und das
bleibt so: der Weg ist WireGuard oder WLAN, nicht ein offener Port.

★ ``PUT`` statt ``POST`` je Tag, mit Datum als Schluessel. Ein Handy schiebt
denselben Tag mehrfach, waehrend die Schritte weiterlaufen. Mit POST entstuenden
Duplikate, und die Summe waere um ein Vielfaches zu hoch.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Tagesschritte
from app.schemas import SchritteEintrag, SchritteOut, SchritteUebersichtOut

router = APIRouter(prefix="/api/schritte", tags=["schritte"])

# Untergrenze, ab der ein Tag als aktiv gilt. Wird fuer die Ableitung des
# Aktivitaetsniveaus gebraucht, nicht als Ziel: ein Ziel gehoert dem Nutzer.
AKTIV_AB_SCHRITTEN = 7500


@router.put("", response_model=list[SchritteOut])
def schritte_melden(eintraege: list[SchritteEintrag], db: Session = Depends(get_db)):
    """Einen oder mehrere Tage melden. Vorhandene Tage werden ueberschrieben.

    Mehrere auf einmal, weil ein Handy nach ein paar Tagen ohne Heimnetz
    genau das braucht: einen Schwung nachtragen statt sieben Einzelaufrufe.
    """
    ergebnis: list[Tagesschritte] = []
    for eintrag in eintraege:
        zeile = (
            db.query(Tagesschritte)
            .filter(Tagesschritte.datum == eintrag.datum)
            .first()
        )
        if zeile is None:
            zeile = Tagesschritte(datum=eintrag.datum, schritte=eintrag.schritte)
            db.add(zeile)
        # ★ Nur nach oben korrigieren, wenn dieselbe Quelle nachmeldet: Health
        # Connect liefert im Tagesverlauf wachsende Werte, und ein spaeterer
        # Abruf mit einem kleineren Wert waere eine unvollstaendige Abfrage,
        # kein Rueckgang. Ein Wechsel der Quelle setzt dagegen neu.
        if zeile.quelle == eintrag.quelle and eintrag.schritte < zeile.schritte:
            pass
        else:
            zeile.schritte = eintrag.schritte
        if eintrag.distanz_m is not None:
            zeile.distanz_m = eintrag.distanz_m
        if eintrag.aktive_kcal is not None:
            zeile.aktive_kcal = eintrag.aktive_kcal
        zeile.quelle = eintrag.quelle
        ergebnis.append(zeile)
    db.commit()
    return [SchritteOut.model_validate(z) for z in ergebnis]


@router.get("", response_model=SchritteUebersichtOut)
def schritte_lesen(tage: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    ab = date.today() - timedelta(days=tage - 1)
    zeilen = (
        db.query(Tagesschritte)
        .filter(Tagesschritte.datum >= ab)
        .order_by(Tagesschritte.datum)
        .all()
    )
    werte = [z.schritte for z in zeilen]
    heute = next((z for z in zeilen if z.datum == date.today()), None)
    return SchritteUebersichtOut(
        tage=[SchritteOut.model_validate(z) for z in zeilen],
        heute=heute.schritte if heute else None,
        schnitt=round(sum(werte) / len(werte)) if werte else None,
        aktive_tage=sum(1 for w in werte if w >= AKTIV_AB_SCHRITTEN),
        erfasste_tage=len(werte),
    )


@router.get("/letzter-tag")
def letzter_tag(db: Session = Depends(get_db)):
    """Der juengste erfasste Tag. Die App fragt danach, bevor sie nachtraegt.

    Ohne diese Auskunft muesste sie entweder immer dreissig Tage schicken oder
    raten, ab wann eine Luecke besteht.
    """
    zeile = db.query(Tagesschritte).order_by(Tagesschritte.datum.desc()).first()
    return {"datum": zeile.datum.isoformat() if zeile else None}
