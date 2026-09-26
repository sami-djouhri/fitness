"""Achievement routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AchievementOut
from app.services.achievements import AchievementService

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=list[AchievementOut])
def list_achievements(db: Session = Depends(get_db)):
    svc = AchievementService(db)
    return svc.get_all()


@router.get("/recent", response_model=list[AchievementOut])
def recent_achievements(limit: int = 5, db: Session = Depends(get_db)):
    svc = AchievementService(db)
    return svc.get_recent(limit=limit)


@router.post("/check", response_model=list[AchievementOut])
def check_achievements(db: Session = Depends(get_db)):
    svc = AchievementService(db)
    newly = svc.check_and_unlock()
    db.commit()
    return newly
