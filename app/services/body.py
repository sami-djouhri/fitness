"""Body metrics service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.domain import DomainError
from app.models import BodyMetric
from app.schemas import BodyMetricCreate, BodyTrendPoint


class BodyService:
    def __init__(self, db: Session):
        self.db = db

    def list_metrics(self, limit: int = 90, offset: int = 0) -> list[BodyMetric]:
        return (
            self.db.query(BodyMetric)
            .order_by(BodyMetric.date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, data: BodyMetricCreate) -> BodyMetric:
        existing = self.db.query(BodyMetric).filter(BodyMetric.date == data.date).first()
        if existing:
            # Update existing entry for that date
            existing.weight_kg = data.weight_kg
            if data.body_fat_pct is not None:
                existing.body_fat_pct = data.body_fat_pct
            if data.waist_cm is not None:
                existing.waist_cm = data.waist_cm
            if data.notes is not None:
                existing.notes = data.notes
            return existing
        metric = BodyMetric(
            date=data.date,
            weight_kg=data.weight_kg,
            body_fat_pct=data.body_fat_pct,
            waist_cm=data.waist_cm,
            notes=data.notes,
        )
        self.db.add(metric)
        return metric

    def delete(self, metric_id: int) -> None:
        metric = self.db.get(BodyMetric, metric_id)
        if not metric:
            raise DomainError("Messung nicht gefunden", {"metric_id": metric_id})
        self.db.delete(metric)

    def get_trend(self, days: int = 90) -> list[BodyTrendPoint]:
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
        metrics = (
            self.db.query(BodyMetric)
            .filter(BodyMetric.date >= cutoff)
            .order_by(BodyMetric.date.asc())
            .all()
        )
        if not metrics:
            return []

        result: list[BodyTrendPoint] = []
        window = 7
        for i, m in enumerate(metrics):
            start = max(0, i - window + 1)
            window_values = [metrics[j].weight_kg for j in range(start, i + 1)]
            avg = sum(window_values) / len(window_values)
            result.append(BodyTrendPoint(
                date=m.date,
                weight_kg=m.weight_kg,
                moving_avg=round(avg, 2),
            ))
        return result
