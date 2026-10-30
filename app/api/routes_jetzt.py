"""Die eine Frage, mit der man diese App oeffnet: was trainiere ich jetzt.

Gegenstueck zum Kalender. Der plant, **wann** Zeit fuer Training ist, und
reicht die Dauer seines Trainingsblocks hier herein; diese Route beantwortet,
**was** in diese Dauer gehoert. Begruendung der Trennung in
``services/jetzt.py``.

Die Dauer ist ein Parameter und keine Annahme. Ohne sie fragt der Dienst seit
dem 2026-10-24 den Kalender (``minuten_quelle='kalender'``) und faellt erst
danach auf eine ausgewiesene Vorgabe zurueck (``'vorgabe'``), statt eine Zahl
zu erfinden, die wie eine gemessene aussieht.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TrainingJetztOut
from app.services.jetzt import JetztService

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("/jetzt", response_model=TrainingJetztOut)
def jetzt(
    minuten: int | None = Query(
        None,
        ge=1,
        le=300,
        description="Verfuegbare Minuten. Fehlt der Wert, holt der Dienst den "
                    "Trainingsblock beim Kalender und rechnet erst danach mit "
                    "einer Vorgabe, die er als solche ausweist.",
    ),
    db: Session = Depends(get_db),
):
    """Die Einheit fuer jetzt: Plan, Zeit und Erholung zusammengefuehrt."""
    return JetztService(db).training(minuten=minuten)
