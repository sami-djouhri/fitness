"""Koerpermasse: 13 Umfaenge, Messanleitung und Verlauf (seit 2026-11-07).

Der Bauchumfang lag vorher am Gewichtseintrag (``BodyMetric.waist_cm``). Er
fliesst hier mit ein, damit Altwerte nicht verschwinden: an einem Tag mit
beiden Quellen gewinnt der Messdurchgang.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BodyMetric, Koerpermass
from app.schemas import KoerpermasseOut, MassStand, MasspunktOut, MessdurchgangIn
from app.services import koerpermasse

router = APIRouter(prefix="/api/body/masse", tags=["body"])

UNTEN_CM, OBEN_CM = 10.0, 250.0


def _verlauf(db: Session, mass: str) -> list[tuple[date, float]]:
    """Alle Werte eines Masses, aelteste zuerst, je Tag einer."""
    je_tag: dict[date, float] = {}
    if mass == "bauch":
        for m in db.query(BodyMetric).filter(BodyMetric.waist_cm.isnot(None)).all():
            je_tag[m.date] = m.waist_cm
    for z in db.query(Koerpermass).filter(Koerpermass.mass == mass).all():
        je_tag[z.datum] = z.wert_cm
    return sorted(je_tag.items())


@router.get("", response_model=KoerpermasseOut)
def masse(db: Session = Depends(get_db)):
    aktuell: dict[str, MassStand] = {}
    for d in koerpermasse.MASSE:
        reihe = _verlauf(db, d.id)
        if not reihe:
            continue
        datum, wert = reihe[-1]
        vorher = reihe[-2] if len(reihe) > 1 else None
        aktuell[d.id] = MassStand(
            wert_cm=wert, datum=datum,
            vorher_cm=vorher[1] if vorher else None,
            vorher_datum=vorher[0] if vorher else None,
        )
    return KoerpermasseOut(
        allgemein=koerpermasse.ALLGEMEIN,
        definitionen=koerpermasse.definitionen(),
        aktuell=aktuell,
    )


@router.put("", response_model=KoerpermasseOut)
def messdurchgang(eingabe: MessdurchgangIn, db: Session = Depends(get_db)):
    """Einen Durchgang speichern; ein Mass desselben Tages wird ersetzt."""
    unbekannt = sorted(set(eingabe.werte) - koerpermasse.KENNUNGEN)
    if unbekannt:
        raise HTTPException(422, f"Unbekannte Masse: {', '.join(unbekannt)}")
    falsch = sorted(k for k, v in eingabe.werte.items() if not UNTEN_CM <= v <= OBEN_CM)
    if falsch:
        raise HTTPException(422, f"Außerhalb von {UNTEN_CM:.0f} bis {OBEN_CM:.0f} cm: {', '.join(falsch)}")
    for mass, wert in eingabe.werte.items():
        zeile = (
            db.query(Koerpermass)
            .filter(Koerpermass.datum == eingabe.datum, Koerpermass.mass == mass)
            .first()
        )
        if zeile is None:
            db.add(Koerpermass(datum=eingabe.datum, mass=mass, wert_cm=round(wert, 1)))
        else:
            zeile.wert_cm = round(wert, 1)
    db.commit()
    return masse(db)


@router.get("/verlauf", response_model=list[MasspunktOut])
def verlauf(mass: str = Query(...), db: Session = Depends(get_db)):
    if mass not in koerpermasse.KENNUNGEN:
        raise HTTPException(404, f"Unbekanntes Mass: {mass}")
    return [MasspunktOut(datum=d, wert_cm=w) for d, w in _verlauf(db, mass)]
