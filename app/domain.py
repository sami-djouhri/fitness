"""Core domain primitives: errors, enums, helpers."""

from __future__ import annotations

import enum


class DomainError(Exception):
    """Raised for business-rule violations."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class Category(str, enum.Enum):
    BRUST = "Brust"
    RUECKEN = "Rücken"
    SCHULTERN = "Schultern"
    ARME = "Arme"
    BEINE = "Beine"
    CORE = "Core"
    CARDIO = "Cardio"
    DEHNUNG = "Dehnung"


class Equipment(str, enum.Enum):
    LANGHANTEL = "Langhantel"
    KURZHANTEL = "Kurzhantel"
    KABELZUG = "Kabelzug"
    MASCHINE = "Maschine"
    KOERPERGEWICHT = "Körpergewicht"
    BAND = "Band"
    KETTLEBELL = "Kettlebell"


def derive_activity_level(workouts_last_7_days: int) -> str:
    if workouts_last_7_days == 0:
        return "sedentary"
    if workouts_last_7_days <= 2:
        return "light"
    if workouts_last_7_days <= 4:
        return "moderate"
    if workouts_last_7_days <= 6:
        return "active"
    return "very_active"
