"""Volumen, Frische, Empfehlungen und die Muskel-Registry.

Diese Routen loesen die Zahlen ab, die vorher in ``routes_progress`` steckten
und dort je Ansicht anders gerechnet wurden. Alles hier kommt aus
``services/volumen.py`` und ``services/empfehlung.py``, also aus je einer
Quelle.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    EinheitsvorschlagOut, GruppenempfehlungOut, GruppenfrischeOut,
    GruppenwocheOut, MuskelOut, MuskelgruppeOut, MuskelstandOut,
    RegistryOut, UebungsvorschlagOut,
)
from app.services.empfehlung import EmpfehlungsService
from app.services.muskulatur import GRUPPEN, MUSKELN, REGIONEN
from app.services.profil import ProfilService
from app.services.volumen import VolumenService

router = APIRouter(prefix="/api/analyse", tags=["analyse"])


def _volumen(db: Session) -> VolumenService:
    return VolumenService(db, ProfilService(db).koerpergewicht())


@router.get("/registry", response_model=RegistryOut)
def registry():
    """Regionen, Gruppen und Muskeln als eine Auskunft.

    Das Frontend und die native App bauen daraus ihre Beschriftungen und das
    Koerpermodell. ★ Bewusst eine Route statt drei: die drei Ebenen haengen
    zusammen, und getrennt geladen zeigt die Oberflaeche zwischenzeitlich
    Gruppen ohne Muskeln.
    """
    return RegistryOut(
        regionen=[{"id": rid, "name": rname} for rid, rname in REGIONEN.items()],
        gruppen=[
            MuskelgruppeOut(
                id=g.id, name=g.name, region=g.region, ppl=g.ppl,
                mv=g.mv, mev=g.mev, mav_min=g.mav_min, mav_max=g.mav_max,
                mrv=g.mrv, erholung_stunden=g.erholung_stunden,
            )
            for g in GRUPPEN.values()
        ],
        muskeln=[
            MuskelOut(
                id=m.id, name=m.name, fachname=m.fachname, gruppe=m.gruppe,
                ansicht=m.ansicht, funktion=m.funktion,
            )
            for m in MUSKELN.values()
        ],
    )


@router.get("/volumen", response_model=list[GruppenwocheOut])
def volumen(tage: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    return [GruppenwocheOut(**w.__dict__) for w in _volumen(db).woche(tage)]


@router.get("/frische", response_model=list[GruppenfrischeOut])
def frische(db: Session = Depends(get_db)):
    return [GruppenfrischeOut(**f.__dict__) for f in _volumen(db).frische()]


@router.get("/verlauf")
def verlauf(wochen: int = Query(8, ge=1, le=52), db: Session = Depends(get_db)):
    return _volumen(db).verlauf(wochen)


@router.get("/muskeln", response_model=dict[str, MuskelstandOut])
def je_muskel(tage: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    """Saetze, Volumen und Tage seit der letzten Belastung, je Einzelmuskel.

    Das ist die Zahl, die das Koerpermodell einfaerbt. Sie entsteht auf
    Muskelebene und nicht auf Gruppenebene: sonst leuchten alle vier
    Quadrizeps-Koepfe gleich, obwohl Beinstrecker und Kniebeuge sie
    verschieden treffen.
    """
    roh = _volumen(db).je_muskel(tage)
    return {mid: MuskelstandOut(**werte) for mid, werte in roh.items()}


@router.get("/empfehlung", response_model=list[GruppenempfehlungOut])
def empfehlung(gruppen: int = Query(3, ge=1, le=10), db: Session = Depends(get_db)):
    svc = EmpfehlungsService(db)
    ergebnis = svc.empfehlen(anzahl_gruppen=gruppen)
    db.commit()   # ProfilService legt beim ersten Zugriff das Profil an
    return [
        GruppenempfehlungOut(
            gruppe=g.gruppe, name=g.name, region=g.region, punkte=g.punkte,
            bedarf=g.bedarf, frische=g.frische, begruendung=g.begruendung,
            uebungen=[UebungsvorschlagOut(**u.__dict__) for u in g.uebungen],
        )
        for g in ergebnis
    ]


@router.get("/einheit", response_model=EinheitsvorschlagOut)
def einheit(minuten: int = Query(45, ge=10, le=180), db: Session = Depends(get_db)):
    """Eine ganze Einheit, die in die verfuegbare Zeit passt."""
    svc = EmpfehlungsService(db)
    roh = svc.einheit_vorschlagen(minuten)
    db.commit()
    return EinheitsvorschlagOut(
        dauer_minuten=roh["dauer_minuten"],
        geplante_minuten=roh["geplante_minuten"],
        gruppen=roh["gruppen"],
        uebungen=[UebungsvorschlagOut(**u.__dict__) for u in roh["uebungen"]],
    )
