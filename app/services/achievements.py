"""Achievement system service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Achievement, PersonalRecord, UserAchievement, Workout, WorkoutSet
from app.schemas import AchievementOut
from app.services.satzfilter import arbeitssatz
from app.services.muscle_map import ALL_REGIONS, MUSCLE_TO_REGION

# Achievement definitions (seeded on first access)
ACHIEVEMENT_DEFS = [
    # Erste Schritte
    {"key": "first_workout", "name": "Erster Schritt", "description": "Erstes Workout abgeschlossen", "icon": "1", "category": "erste_schritte"},
    {"key": "first_week", "name": "Erste Woche", "description": "7 Tage in Folge trainiert", "icon": "7", "category": "erste_schritte"},
    {"key": "first_plan", "name": "Planer", "description": "Ersten Trainingsplan erstellt", "icon": "P", "category": "erste_schritte"},
    # Konsistenz
    {"key": "streak_7", "name": "Wochenkrieger", "description": "7-Tage-Streak erreicht", "icon": "W", "category": "konsistenz"},
    {"key": "streak_30", "name": "Monatsmaschine", "description": "30-Tage-Streak erreicht", "icon": "M", "category": "konsistenz"},
    {"key": "workouts_10", "name": "Durchstarter", "description": "10 Workouts absolviert", "icon": "X", "category": "konsistenz"},
    {"key": "workouts_50", "name": "Stammgast", "description": "50 Workouts absolviert", "icon": "L", "category": "konsistenz"},
    {"key": "workouts_100", "name": "Centurion", "description": "100 Workouts absolviert", "icon": "C", "category": "konsistenz"},
    # Stärke
    {"key": "first_pr", "name": "Rekordbrecher", "description": "Ersten Personal Record aufgestellt", "icon": "R", "category": "staerke"},
    {"key": "prs_10", "name": "PR-Jäger", "description": "10 Personal Records aufgestellt", "icon": "J", "category": "staerke"},
    {"key": "bodyweight_bench", "name": "Bodyweight Bench", "description": "Körpergewicht beim Bankdrücken gedrückt", "icon": "B", "category": "staerke"},
    # Allrounder
    {"key": "all_muscles_week", "name": "Allrounder", "description": "Alle Muskelgruppen in einer Woche trainiert", "icon": "A", "category": "allrounder"},
    {"key": "exercises_10", "name": "Vielseitig", "description": "10 verschiedene Übungen ausgeführt", "icon": "V", "category": "allrounder"},
    # Volumen
    {"key": "volume_10k_week", "name": "Volumen-König", "description": "10.000 kg Wochenvolumen erreicht", "icon": "K", "category": "volumen"},
    {"key": "volume_100k_total", "name": "Tonnenweise", "description": "100.000 kg Gesamtvolumen bewegt", "icon": "T", "category": "volumen"},
    # Disziplin
    {"key": "early_bird", "name": "Frühaufsteher", "description": "Workout vor 7 Uhr gestartet", "icon": "F", "category": "disziplin"},
    {"key": "night_owl", "name": "Nachteule", "description": "Workout nach 22 Uhr gestartet", "icon": "N", "category": "disziplin"},
    {"key": "weekend_warrior", "name": "Wochenend-Krieger", "description": "10 Wochenend-Workouts absolviert", "icon": "S", "category": "disziplin"},
]


class AchievementService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_achievements_exist(self) -> None:
        """Seed achievement definitions if they don't exist."""
        existing = self.db.query(Achievement).count()
        if existing >= len(ACHIEVEMENT_DEFS):
            return
        for defn in ACHIEVEMENT_DEFS:
            exists = self.db.query(Achievement).filter(Achievement.key == defn["key"]).first()
            if not exists:
                self.db.add(Achievement(**defn))
        self.db.flush()

    def get_all(self) -> list[AchievementOut]:
        """Return all achievements with unlock status."""
        self.ensure_achievements_exist()
        achievements = self.db.query(Achievement).order_by(Achievement.category, Achievement.id).all()
        unlocked = {
            ua.achievement_id: ua.unlocked_at
            for ua in self.db.query(UserAchievement).all()
        }
        return [
            AchievementOut(
                id=a.id,
                key=a.key,
                name=a.name,
                description=a.description,
                icon=a.icon,
                category=a.category,
                unlocked_at=unlocked.get(a.id),
            )
            for a in achievements
        ]

    def get_recent(self, limit: int = 5) -> list[AchievementOut]:
        """Return recently unlocked achievements."""
        self.ensure_achievements_exist()
        uas = (
            self.db.query(UserAchievement)
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(limit)
            .all()
        )
        return [
            AchievementOut(
                id=ua.achievement.id,
                key=ua.achievement.key,
                name=ua.achievement.name,
                description=ua.achievement.description,
                icon=ua.achievement.icon,
                category=ua.achievement.category,
                unlocked_at=ua.unlocked_at,
            )
            for ua in uas
        ]

    def check_and_unlock(self) -> list[AchievementOut]:
        """Check all achievement conditions and unlock new ones. Returns newly unlocked."""
        self.ensure_achievements_exist()

        already_unlocked = {
            ua.achievement.key
            for ua in self.db.query(UserAchievement).join(Achievement).all()
        }
        achievement_map = {a.key: a for a in self.db.query(Achievement).all()}

        newly_unlocked: list[AchievementOut] = []
        now = datetime.now(timezone.utc)

        def unlock(key: str) -> None:
            if key in already_unlocked or key not in achievement_map:
                return
            a = achievement_map[key]
            ua = UserAchievement(achievement_id=a.id, unlocked_at=now)
            self.db.add(ua)
            already_unlocked.add(key)
            newly_unlocked.append(AchievementOut(
                id=a.id, key=a.key, name=a.name, description=a.description,
                icon=a.icon, category=a.category, unlocked_at=now,
            ))

        # Count workouts
        workout_count = self.db.query(Workout).filter(Workout.finished_at.isnot(None)).count()
        if workout_count >= 1:
            unlock("first_workout")
        if workout_count >= 10:
            unlock("workouts_10")
        if workout_count >= 50:
            unlock("workouts_50")
        if workout_count >= 100:
            unlock("workouts_100")

        # PR count
        pr_count = self.db.query(PersonalRecord).count()
        if pr_count >= 1:
            unlock("first_pr")
        if pr_count >= 10:
            unlock("prs_10")

        # Total volume
        total_vol = (
            self.db.query(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps))
            .filter(
                *arbeitssatz(),
                WorkoutSet.weight_kg.isnot(None),
                WorkoutSet.reps.isnot(None),
            )
            .scalar()
        ) or 0
        if total_vol >= 100_000:
            unlock("volume_100k_total")

        # Weekly volume (current week)
        week_start = now.date() - timedelta(days=now.date().weekday())
        week_vol = (
            self.db.query(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps))
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(
                Workout.started_at >= datetime.combine(week_start, datetime.min.time()),
                *arbeitssatz(),
                WorkoutSet.weight_kg.isnot(None),
                WorkoutSet.reps.isnot(None),
            )
            .scalar()
        ) or 0
        if week_vol >= 10_000:
            unlock("volume_10k_week")

        # Distinct exercises used
        distinct_exercises = self.db.query(WorkoutSet.exercise_id).distinct().count()
        if distinct_exercises >= 10:
            unlock("exercises_10")

        # All muscles in a week: check regions trained this week
        week_sets = (
            self.db.query(WorkoutSet)
            .join(Workout, WorkoutSet.workout_id == Workout.id)
            .filter(Workout.started_at >= datetime.combine(week_start, datetime.min.time()))
            .all()
        )
        week_regions: set[str] = set()
        for ws in week_sets:
            if ws.exercise:
                for m in ws.exercise.primary_muscles:
                    for r in MUSCLE_TO_REGION.get(m, []):
                        week_regions.add(r)
        if week_regions >= set(ALL_REGIONS):
            unlock("all_muscles_week")

        # Weekend workouts
        weekend_count = (
            self.db.query(Workout)
            .filter(
                Workout.finished_at.isnot(None),
                func.strftime("%w", Workout.started_at).in_(["0", "6"]),
            )
            .count()
        )
        if weekend_count >= 10:
            unlock("weekend_warrior")

        self.db.flush()
        return newly_unlocked
