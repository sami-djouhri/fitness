"""ORM models: Exercise, Plan, PlanDay, PlanExercise, Workout, WorkoutSet, BodyMetric, PersonalRecord, Achievement, UserAchievement."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base

# Multi-Tenant: Owner aller Alt-Daten + server_default fuer neue Tenant-Zeilen.
_OWNER = settings.DEFAULT_OWNER_SUB


def _owner_col() -> Mapped[str]:
    return mapped_column(String(128), nullable=False, index=True, server_default=_OWNER)


def _json_default(val: Any) -> str | None:
    if val is None:
        return None
    return json.dumps(val, ensure_ascii=False)


def _json_load(raw: str | None) -> Any:
    if raw is None:
        return None
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Exercise – Übungskatalog
# ---------------------------------------------------------------------------

class Exercise(Base):
    __tablename__ = "exercise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    equipment: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_muscles_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_muscles_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)
    # ★ Diese Spalte ist seit 2026-09 kein Nutzerzustand mehr, sondern nur noch
    # die Vorbelegung fuer den Katalog. Wer eine Uebung ab- oder anwaehlt,
    # schreibt in ``exercise_selection``: ``is_selected`` sass auf dem
    # GETEILTEN Katalog, ein Abwaehlen galt damit fuer alle Mandanten.
    is_selected: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # NULL = Katalogeintrag aus dem Seed: fuer alle sichtbar, von niemandem
    # aenderbar. Sonst die Kennung dessen, der die Uebung angelegt hat: nur
    # fuer ihn sichtbar und nur von ihm aenderbar.
    created_by_sub: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    # --- seit 2026-09: feinere Zuordnung, Ausruestung, Ausfuehrung ---

    # Muskelkennung aus services/muskulatur.py auf einen Anteil zwischen 0 und 1.
    # Loest primary/secondary ab: die Zweiteilung zwang dazu, einen Muskel
    # entweder voll oder gar nicht zu zaehlen. Die alten Felder bleiben
    # befuellt, damit aeltere Clients und selbst angelegte Uebungen
    # weiterlaufen.
    muskel_anteile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Geraete, ohne die die Uebung nicht geht (services/ausruestung.py).
    # ★ Nicht dasselbe wie ``equipment``: Klimmzuege stehen unter
    # "Körpergewicht" und brauchen trotzdem eine Stange. Genau deshalb galten
    # sie bisher als ueberall machbar.
    benoetigt_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bewegungsmuster. Traegt die 3D-Vorfuehrung, siehe data/uebungskatalog.py.
    muster: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # ★★ Anteil des Koerpergewichts, den die Uebung bewegt. Ohne diesen Wert
    # erzeugt jede Koerpergewichtsuebung null Volumen, weil ``weight_kg`` leer
    # bleibt. Wer zu Hause trainiert, sah in der Statistik deshalb eine
    # Nulllinie. 0 heisst "nicht koerpergewichtsbasiert" (Hanteluebung).
    kg_anteil: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    griff: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Progressionsreihe fuer Koerpergewichtstraining plus Stufe darin.
    reihe: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    stufe: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    einseitig: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # Zeit statt Wiederholungen (Plank, Hang, Cardio).
    ist_zeit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    wdh_min: Mapped[int] = mapped_column(Integer, default=8, server_default="8")
    wdh_max: Mapped[int] = mapped_column(Integer, default=12, server_default="12")
    pause_s: Mapped[int] = mapped_column(Integer, default=90, server_default="90")
    ausfuehrung: Mapped[str | None] = mapped_column(Text, nullable=True)
    fehler: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def primary_muscles(self) -> list[str]:
        return _json_load(self.primary_muscles_json) or []

    @primary_muscles.setter
    def primary_muscles(self, val: list[str]) -> None:
        self.primary_muscles_json = _json_default(val)

    @property
    def secondary_muscles(self) -> list[str]:
        return _json_load(self.secondary_muscles_json) or []

    @secondary_muscles.setter
    def secondary_muscles(self, val: list[str]) -> None:
        self.secondary_muscles_json = _json_default(val)

    @property
    def muskel_anteile(self) -> dict[str, float]:
        """Muskelkennung auf Anteil. Leer bei selbst angelegten Uebungen.

        Der Aufrufer faellt dann auf ``primary_muscles``/``secondary_muscles``
        zurueck (services/anteile.py). Hier bewusst kein Fallback: eine
        Eigenschaft, die stillschweigend etwas anderes liefert als das Feld
        heisst, ist schwerer zu durchschauen als ein leeres Ergebnis.
        """
        return _json_load(self.muskel_anteile_json) or {}

    @muskel_anteile.setter
    def muskel_anteile(self, val: dict[str, float]) -> None:
        self.muskel_anteile_json = _json_default(val)

    @property
    def benoetigt(self) -> list[str]:
        return _json_load(self.benoetigt_json) or []

    @benoetigt.setter
    def benoetigt(self, val: list[str]) -> None:
        self.benoetigt_json = _json_default(val)


# ---------------------------------------------------------------------------
# Plan – Trainingsplan
# ---------------------------------------------------------------------------

class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    days: Mapped[list[PlanDay]] = relationship(
        "PlanDay", back_populates="plan", cascade="all, delete-orphan",
        order_by="PlanDay.sort_order",
    )


# ---------------------------------------------------------------------------
# PlanDay – Trainingstag im Plan
# ---------------------------------------------------------------------------

class PlanDay(Base):
    __tablename__ = "plan_day"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped[Plan] = relationship("Plan", back_populates="days")
    exercises: Mapped[list[PlanExercise]] = relationship(
        "PlanExercise", back_populates="plan_day", cascade="all, delete-orphan",
        order_by="PlanExercise.sort_order",
    )


# ---------------------------------------------------------------------------
# PlanExercise – Übung im Trainingstag
# ---------------------------------------------------------------------------

class PlanExercise(Base):
    __tablename__ = "plan_exercise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    plan_day_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_day.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    target_sets: Mapped[int] = mapped_column(Integer, default=3)
    target_reps_min: Mapped[int] = mapped_column(Integer, default=8)
    target_reps_max: Mapped[int] = mapped_column(Integer, default=12)
    target_rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_seconds: Mapped[int] = mapped_column(Integer, default=90)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan_day: Mapped[PlanDay] = relationship("PlanDay", back_populates="exercises")
    exercise: Mapped[Exercise] = relationship("Exercise")


# ---------------------------------------------------------------------------
# Workout – durchgeführtes Training
# ---------------------------------------------------------------------------

class Workout(Base):
    __tablename__ = "workout"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    plan_day_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("plan_day.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pre-workout readiness check
    fatigue_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pre_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan_day: Mapped[PlanDay | None] = relationship("PlanDay")
    sets: Mapped[list[WorkoutSet]] = relationship(
        "WorkoutSet", back_populates="workout", cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


# ---------------------------------------------------------------------------
# WorkoutSet – einzelner Satz
# ---------------------------------------------------------------------------

class WorkoutSet(Base):
    __tablename__ = "workout_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workout.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise.id"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    set_type: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal")
    group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Abgehakt oder nur geplant. Seit die Session aus dem Trainingstag
    # vorbefuellt wird, existiert ein Satz auch dann schon, wenn er noch nicht
    # gemacht ist. Ohne diese Unterscheidung zaehlte die Statistik fuenf
    # geplante Uebungen als absolviert, sobald man nach zwei aufhoert.
    # Vorbelegung True: ein von Hand eingetragener Satz ist ein gemachter Satz,
    # das war das Verhalten vor dem Vorbefuellen.
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workout: Mapped[Workout] = relationship("Workout", back_populates="sets")
    exercise: Mapped[Exercise] = relationship("Exercise")


# ---------------------------------------------------------------------------
# BodyMetric – Körperdaten
# ---------------------------------------------------------------------------

class BodyMetric(Base):
    __tablename__ = "body_metric"
    __table_args__ = (
        UniqueConstraint("owner_sub", "date", name="uq_body_metric_owner_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# PersonalRecord – PR-Tracking
# ---------------------------------------------------------------------------

class PersonalRecord(Base):
    __tablename__ = "personal_record"
    __table_args__ = (
        UniqueConstraint("owner_sub", "exercise_id", "pr_type", name="uq_owner_exercise_pr_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise.id"), nullable=False)
    pr_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    achieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    workout_set_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("workout_set.id"), nullable=True)

    exercise: Mapped[Exercise] = relationship("Exercise")


# ---------------------------------------------------------------------------
# Achievement – Gamification
# ---------------------------------------------------------------------------

class Achievement(Base):
    __tablename__ = "achievement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)


class AnstossMerker(Base):
    """Gedaechtnis des Benachrichtigungskanals, je Mandant.

    Haelt fest, was schon gemeldet wurde, damit ein zweimal taeglich laufender
    Anstoss nicht zweimal dasselbe sagt. Lag vorher in zwei Dateien neben
    einem Bash-Skript und war damit nicht mandantenfaehig: bei zwei Nutzern
    haette der eine die Erinnerung des anderen unterdrueckt.
    """

    __tablename__ = "anstoss_merker"
    __table_args__ = (
        UniqueConstraint("owner_sub", "schluessel", name="uq_anstoss_owner_schluessel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    schluessel: Mapped[str] = mapped_column(String(200), nullable=False)
    gemeldet_am: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class ExerciseSelection(Base):
    """Welche Uebungen ein Mandant in seinem Studio hat.

    Der Zustand sass vorher als ``is_selected`` auf dem geteilten Katalog.
    In einem Mehrpersonen-Betrieb hiess das: wer eine Uebung abwaehlt, weil es
    das Geraet in seinem Studio nicht gibt, waehlt sie allen anderen mit ab.
    Aufgefallen waere das niemandem, denn kaputt ist dabei nichts.

    Kein Eintrag bedeutet ausgewaehlt. Ein neuer Nutzer sieht damit den ganzen
    Katalog, ohne dass beim Anlegen 67 Zeilen geschrieben werden muessen.
    """

    __tablename__ = "exercise_selection"
    __table_args__ = (
        UniqueConstraint("owner_sub", "exercise_id", name="uq_selection_owner_exercise"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercise.id", ondelete="CASCADE"), nullable=False
    )
    is_selected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Nutzerprofil(Base):
    """Was die App ueber den Menschen wissen muss, um zu ihm zu passen.

    Bis hierhin gab es das nicht, und daran hingen zwei Befunde: die
    Empfehlungslogik schlug Beinpresse und Kabelzug vor, weil sie keinen
    Bestand kannte, und der Gewichtsvorschlag rechnete in 2,5-kg-Schritten,
    die eine verstellbare Kurzhantel gar nicht hergibt.

    Genau ein Datensatz je Mandant. Fehlt er, gelten die Vorbelegungen unten,
    und die App verhaelt sich wie vorher.
    """

    __tablename__ = "nutzerprofil"
    __table_args__ = (
        UniqueConstraint("owner_sub", name="uq_nutzerprofil_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()

    # Ausruestung: Kennungen aus services/ausruestung.py. Leer heisst
    # ausdruecklich "nur Koerpergewicht", nicht "noch nicht ausgefuellt";
    # dafuer gibt es ``eingerichtet``.
    geraete_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    eingerichtet: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # einsteiger | fortgeschritten | erfahren. Verschiebt die Volumen-Landmarks
    # und die Erwartung an den Fortschritt je Woche.
    erfahrung: Mapped[str] = mapped_column(
        String(20), default="einsteiger", server_default="einsteiger")
    # hypertrophie | kraft | ausdauer | erhaltung
    ziel: Mapped[str] = mapped_column(
        String(20), default="hypertrophie", server_default="hypertrophie")
    trainingstage_pro_woche: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3")

    # ★ Der kleinste Sprung, den die vorhandene Ausruestung ueberhaupt zulaesst.
    # Ein Vorschlag "+2,5 kg" ist wertlos, wenn die verstellbare Kurzhantel in
    # 2-kg-Stufen geht. Der Vorschlag wird darauf gerundet.
    gewichtsschritt_kg: Mapped[float] = mapped_column(
        Float, default=2.5, server_default="2.5")
    kurzhantel_max_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Fuer Kraftstandards und die Last bei Koerpergewichtsuebungen. Wird aus
    # der letzten Koerpermessung nachgezogen, sobald es eine gibt.
    koerpergewicht_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    koerpergroesse_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    geburtsjahr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # m | w | divers | keine_angabe. Nur fuer die Kraftstandards, die je
    # Geschlecht andere Verhaeltniszahlen haben.
    geschlecht: Mapped[str] = mapped_column(
        String(15), default="keine_angabe", server_default="keine_angabe")

    # Einschraenkungen, die Uebungen ausschliessen (Knie, Schulter, Ruecken).
    # Freitext-Kennungen, siehe services/einschraenkungen.py.
    einschraenkungen_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    aktualisiert_am: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    @property
    def geraete(self) -> list[str]:
        return _json_load(self.geraete_json) or []

    @geraete.setter
    def geraete(self, val: list[str]) -> None:
        self.geraete_json = _json_default(val)

    @property
    def einschraenkungen(self) -> list[str]:
        return _json_load(self.einschraenkungen_json) or []

    @einschraenkungen.setter
    def einschraenkungen(self, val: list[str]) -> None:
        self.einschraenkungen_json = _json_default(val)


class Tagesschritte(Base):
    """Schritte je Tag, vom Handy geschoben.

    Ein Datensatz je Mandant und Tag. Die native App liest sie aus Health
    Connect und traegt sie nach, sobald sie das Heimnetz erreicht: nach aussen
    ist von diesem Dienst nichts erreichbar, und das soll so bleiben.

    ★ ``quelle`` haelt fest, woher der Wert kommt. Ohne das Feld waere ein
    von Hand eingetragener Wert von einem gemessenen nicht zu unterscheiden,
    und die Ableitung des Aktivitaetsniveaus wuerde beides gleich gewichten.
    """

    __tablename__ = "tagesschritte"
    __table_args__ = (
        UniqueConstraint("owner_sub", "datum", name="uq_schritte_owner_datum"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    datum: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    schritte: Mapped[int] = mapped_column(Integer, nullable=False)
    distanz_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    aktive_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    # health_connect | manuell | geschaetzt
    quelle: Mapped[str] = mapped_column(
        String(20), default="manuell", server_default="manuell")
    gemeldet_am: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class UserAchievement(Base):
    __tablename__ = "user_achievement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_sub: Mapped[str] = _owner_col()
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievement.id"), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    achievement: Mapped[Achievement] = relationship("Achievement")
