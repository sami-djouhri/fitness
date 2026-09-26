"""Body metrics routes."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BodyMetric
from app.schemas import BodyMetricCreate, BodyMetricOut, BodyTrendPoint, MealprepTargetsOut
from app.services import mealprep_adapter
from app.services.body import BodyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/body", tags=["body"])


def _out(m: BodyMetric) -> BodyMetricOut:
    return BodyMetricOut(
        id=m.id,
        date=m.date,
        weight_kg=m.weight_kg,
        body_fat_pct=m.body_fat_pct,
        waist_cm=m.waist_cm,
        notes=m.notes,
    )


@router.get("/metrics", response_model=list[BodyMetricOut])
def list_metrics(
    limit: int = Query(90, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    svc = BodyService(db)
    return [_out(m) for m in svc.list_metrics(limit=limit, offset=offset)]


def _an_mealprep(
    weight_kg: float,
    body_fat_pct: float | None,
    waist_cm: float | None,
    metric_date: str | None,
    owner_sub: str,
) -> None:
    """Laeuft im Hintergrund-Thread, deshalb eine eigene Ereignisschleife.

    Die Antwort an die App darf nicht auf MealPrep warten: der Dienst kann
    schlafen oder weg sein, und eine Gewichtseingabe soll nicht fuenf Sekunden
    haengen, nur weil die Kopplung hakt.

    Bewusst nur einfache Werte als Argumente, kein ORM-Objekt: die Session ist
    beim Ausfuehren schon geschlossen.

    ★ Und bewusst mit eigenem Fangnetz. Eine Ausnahme in einer
    Hintergrundaufgabe reisst in Starlette die Antwort mit, die der Nutzer
    gerade bekommen hat. Die eigene Erfassung darf nicht daran haengen, dass
    der Nachbardienst antwortet.
    """
    try:
        asyncio.run(mealprep_adapter.sync_body_metric(
            weight_kg=weight_kg,
            body_fat_pct=body_fat_pct,
            waist_cm=waist_cm,
            metric_date=metric_date,
            owner_sub=owner_sub,
        ))
    except Exception:
        logger.warning("MealPrep: Weitergabe der Koerperdaten fehlgeschlagen", exc_info=True)


@router.post("/metrics", response_model=BodyMetricOut, status_code=201)
def create_metric(
    body: BodyMetricCreate,
    hintergrund: BackgroundTasks,
    db: Session = Depends(get_db),
):
    svc = BodyService(db)
    metric = svc.create(body)
    db.commit()
    db.refresh(metric)

    # Das Gewicht wandert nach MealPrep, das daraus Grundumsatz und
    # Kalorienziel rechnet. Vorher war dieser Weg gebaut und wurde nie
    # gerufen: man trug sein Gewicht in beiden Apps ein.
    hintergrund.add_task(
        _an_mealprep,
        metric.weight_kg,
        metric.body_fat_pct,
        metric.waist_cm,
        metric.date.isoformat() if metric.date else None,
        db.info.get("owner_sub") or "",
    )

    return _out(metric)


@router.get("/mealprep-ziele", response_model=MealprepTargetsOut)
async def mealprep_ziele(db: Session = Depends(get_db)):
    """Kalorien- und Makroziele aus MealPrep, fuer die Anzeige neben dem Gewicht."""
    daten = await mealprep_adapter.get_targets(owner_sub=db.info.get("owner_sub") or "")
    if not daten:
        return MealprepTargetsOut(verfuegbar=False)
    return MealprepTargetsOut(
        verfuegbar=True,
        kcal=daten.get("kcal"),
        protein_g=daten.get("protein_g"),
        carbs_g=daten.get("carbs_g"),
        fat_g=daten.get("fat_g"),
        fiber_g=daten.get("fiber_g"),
    )


@router.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(metric_id: int, db: Session = Depends(get_db)):
    svc = BodyService(db)
    svc.delete(metric_id)
    db.commit()


@router.get("/trend", response_model=list[BodyTrendPoint])
def get_trend(days: int = 90, db: Session = Depends(get_db)):
    svc = BodyService(db)
    return svc.get_trend(days=days)
