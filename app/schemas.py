"""Pydantic In/Out schemas."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer


def _als_utc(d: datetime) -> str:
    """Zeitstempel mit Zeitzone ausliefern.

    ★ SQLite speichert die Zeitpunkte ohne Zonenangabe. Pydantic gab sie
    genauso weiter ("2026-09-12T13:06:04"), und die Werte sind UTC. Ein
    Browser liest eine ISO-Zeit ohne Offset aber als ORTSZEIT: der
    Trainings-Timer stand damit im Sommer von der ersten Sekunde an zwei
    Stunden zu hoch, gemessen 2:04:32 bei einer Session, die gerade angelegt
    worden war. Im Code faellt das nicht auf, weil beide Seiten fuer sich
    richtig rechnen.
    """
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.isoformat()


# Ausgabe-Zeitpunkt: immer mit Zonenangabe. Eingaben bleiben ``datetime``,
# dort nimmt Pydantic beides an.
UtcDatetime = Annotated[datetime, PlainSerializer(_als_utc, return_type=str)]


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------

class ExerciseCreate(BaseModel):
    name: str = Field(..., max_length=200)
    category: str
    equipment: str
    primary_muscles: list[str] = []
    secondary_muscles: list[str] = []
    is_compound: bool = False
    notes: str | None = Field(None, max_length=500)


class ExerciseUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    category: str | None = None
    equipment: str | None = None
    primary_muscles: list[str] | None = None
    secondary_muscles: list[str] | None = None
    is_compound: bool | None = None
    notes: str | None = Field(None, max_length=500)


class ExerciseSelectUpdate(BaseModel):
    is_selected: bool


class ExerciseOut(BaseModel):
    id: int
    name: str
    category: str
    equipment: str
    primary_muscles: list[str]
    secondary_muscles: list[str] = []
    is_compound: bool
    is_selected: bool = True
    notes: str | None
    # Selbst angelegt (aenderbar) oder Teil des gemeinsamen Katalogs.
    is_eigene: bool = False

    # --- seit 2026-09 ---
    # Muskelkennung auf Anteil. Traegt die Feinauswahl im Koerpermodell und
    # die Volumenrechnung.
    muskel_anteile: dict[str, float] = {}
    benoetigt: list[str] = []
    muster: str | None = None
    kg_anteil: float = 0.0
    griff: str | None = None
    reihe: str | None = None
    stufe: int = 0
    einseitig: bool = False
    ist_zeit: bool = False
    wdh_min: int = 8
    wdh_max: int = 12
    pause_s: int = 90
    ausfuehrung: str | None = None
    fehler: str | None = None
    # Kann der aktuelle Nutzer sie mit seiner Ausruestung machen? Wird je
    # Anfrage berechnet und nicht gespeichert.
    machbar: bool = True
    fehlt_namen: list[str] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

class PlanExerciseCreate(BaseModel):
    exercise_id: int
    sort_order: int = 0
    target_sets: int = Field(3, ge=1, le=50)
    target_reps_min: int = Field(8, ge=0, le=500)
    target_reps_max: int = Field(12, ge=0, le=500)
    target_rpe: float | None = None
    rest_seconds: int = Field(90, ge=0, le=600)
    notes: str | None = Field(None, max_length=500)


class PlanExerciseUpdate(BaseModel):
    exercise_id: int | None = None
    sort_order: int | None = None
    target_sets: int | None = Field(None, ge=1, le=50)
    target_reps_min: int | None = Field(None, ge=0, le=500)
    target_reps_max: int | None = Field(None, ge=0, le=500)
    target_rpe: float | None = None
    rest_seconds: int | None = Field(None, ge=0, le=600)
    notes: str | None = Field(None, max_length=500)


class PlanExerciseOut(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str = ""
    sort_order: int
    target_sets: int
    target_reps_min: int
    target_reps_max: int
    target_rpe: float | None
    rest_seconds: int
    notes: str | None

    model_config = {"from_attributes": True}


class PlanDayCreate(BaseModel):
    name: str
    day_of_week: int | None = None
    sort_order: int = 0


class PlanDayUpdate(BaseModel):
    name: str | None = None
    day_of_week: int | None = None
    sort_order: int | None = None


class PlanDayOut(BaseModel):
    id: int
    name: str
    day_of_week: int | None
    sort_order: int
    exercises: list[PlanExerciseOut] = []

    model_config = {"from_attributes": True}


class PlanCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=500)
    is_active: bool = False


class PlanUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class PlanOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: UtcDatetime
    days: list[PlanDayOut] = []

    model_config = {"from_attributes": True}


class PlanListOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: UtcDatetime
    day_count: int = 0

    model_config = {"from_attributes": True}


class PlanvorlageOut(BaseModel):
    id: str
    name: str
    beschreibung: str
    tage_pro_woche: int
    # Deckt sich mit den eingestellten Trainingstagen des Nutzers.
    passt: bool = False


# ---------------------------------------------------------------------------
# Workout
# ---------------------------------------------------------------------------

SET_TYPES = {"normal", "warmup", "dropset", "failure", "rest_pause"}


class AktivitaetsniveauOut(BaseModel):
    """Aktivitaetsniveau, abgeleitet aus dem tatsaechlichen Training.

    MealPrep rechnet den Tagesbedarf mit genau diesem Faktor. Vorher stand
    dort ein von Hand gesetztes Auswahlfeld, das nichts vom Training wusste.
    """

    stufe: str
    faktor: float
    begruendung: str
    trainings_pro_woche: float
    trainings_im_fenster: int
    fenster_tage: int
    an_mealprep_uebertragen: bool = False
    # Genug erfasst, um daraus einen Kalorienbedarf abzuleiten. False heisst:
    # die Stufe unten ist eine Rechnung, aber keine Aussage.
    belastbar: bool = False


class MealprepTargetsOut(BaseModel):
    """Tagesziele aus MealPrep. ``verfuegbar`` false heisst: Dienst nicht
    erreichbar oder nicht eingerichtet. Die Fitness-App zeigt dann nichts an,
    statt eine Null zu behaupten."""

    verfuegbar: bool
    kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None


class WorkoutSetCreate(BaseModel):
    exercise_id: int
    set_number: int = Field(..., ge=1)
    weight_kg: float | None = Field(None, ge=0)
    reps: int | None = Field(None, ge=1)
    duration_seconds: int | None = None
    distance_meters: float | None = None
    rpe: float | None = Field(None, ge=1, le=10)
    is_warmup: bool = False
    set_type: str = "normal"
    group_id: str | None = None
    notes: str | None = Field(None, max_length=500)
    # Vorbelegung True: wer einen Satz von Hand eintraegt, hat ihn gemacht.
    # Auf False legt das Vorbefuellen aus dem Trainingstag geplante Saetze an.
    is_completed: bool = True


class WorkoutSetUpdate(BaseModel):
    weight_kg: float | None = None
    reps: int | None = None
    duration_seconds: int | None = None
    distance_meters: float | None = None
    rpe: float | None = None
    is_warmup: bool | None = None
    set_type: str | None = None
    group_id: str | None = None
    notes: str | None = Field(None, max_length=500)
    is_completed: bool | None = None


class WorkoutSetOut(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str = ""
    set_number: int
    weight_kg: float | None
    reps: int | None
    duration_seconds: int | None
    distance_meters: float | None
    rpe: float | None
    is_warmup: bool
    set_type: str = "normal"
    group_id: str | None = None
    notes: str | None
    is_completed: bool = True
    completed_at: UtcDatetime | None = None

    model_config = {"from_attributes": True}


class WorkoutCreate(BaseModel):
    plan_day_id: int | None = None
    name: str = Field("Workout", max_length=200)
    notes: str | None = Field(None, max_length=500)
    fatigue_level: int | None = Field(None, ge=1, le=5)
    sleep_quality: int | None = Field(None, ge=1, le=5)
    motivation: int | None = Field(None, ge=1, le=5)
    pre_notes: str | None = Field(None, max_length=500)
    # Uebungen, mit denen die Session vorbefuellt wird. Bei ``plan_day_id``
    # kommen sie aus dem Trainingstag, hier kann der Aufrufer sie direkt
    # nennen: das Dashboard empfiehlt drei Uebungen und startete bisher ein
    # leeres Training, in dem keine davon stand.
    exercise_ids: list[int] | None = None
    # Vorbefuellen abschaltbar, damit ein Trainingstag auch als reine
    # Namensvorlage startbar bleibt.
    prefill: bool = True


class WorkoutUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    finished_at: datetime | None = None
    notes: str | None = Field(None, max_length=500)
    rating: int | None = Field(None, ge=1, le=5)


class PlanTargetOut(BaseModel):
    """Vorgaben des Trainingstages zu einer Uebung, waehrend der Session.

    Ohne diese Werte kennt das Frontend die gepflegten Ziel-Wiederholungen und
    Pausenzeiten nicht und zeigte fuer jede Uebung dieselben 90 Sekunden.
    """

    exercise_id: int
    exercise_name: str = ""
    target_sets: int
    target_reps_min: int
    target_reps_max: int
    target_rpe: float | None = None
    rest_seconds: int
    notes: str | None = None


class WorkoutOut(BaseModel):
    id: int
    plan_day_id: int | None
    plan_day_name: str | None = None
    name: str
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    notes: str | None
    rating: int | None
    fatigue_level: int | None = None
    sleep_quality: int | None = None
    motivation: int | None = None
    pre_notes: str | None = None
    sets: list[WorkoutSetOut] = []
    plan_targets: list[PlanTargetOut] = []

    model_config = {"from_attributes": True}


class WorkoutListOut(BaseModel):
    id: int
    name: str
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    rating: int | None
    set_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

class BodyMetricCreate(BaseModel):
    date: date
    weight_kg: float
    body_fat_pct: float | None = None
    waist_cm: float | None = None
    notes: str | None = None


class BodyMetricOut(BaseModel):
    id: int
    date: date
    weight_kg: float
    body_fat_pct: float | None
    waist_cm: float | None
    notes: str | None

    model_config = {"from_attributes": True}


class BodyTrendPoint(BaseModel):
    date: date
    weight_kg: float
    moving_avg: float | None = None


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

class ExerciseProgressPoint(BaseModel):
    date: date
    estimated_1rm: float | None = None
    best_set_weight: float | None = None
    best_set_reps: int | None = None
    total_volume: float = 0


class VolumeSummary(BaseModel):
    week_start: date
    total_volume: float
    total_sets: int
    workouts: int


class DashboardSummary(BaseModel):
    workouts_7d: int
    workouts_30d: int
    total_volume_7d: float
    current_streak: int
    last_workout: UtcDatetime | None = None
    # Name und Kennung des Tages, der als naechstes ansteht. Der Name stand
    # schon immer im Schema und wurde nie gefuellt; mit der Kennung kann das
    # Dashboard den Tag direkt starten.
    next_plan_day: str | None = None
    next_plan_day_id: int | None = None
    # Tagestyp aus dem Kalender (feiertag / urlaub / schule / arbeit / frei).
    # None heisst "nicht gemessen" und ist NICHT dasselbe wie "frei": ohne
    # Kalender-Konfiguration oder bei dessen Ausfall sagt die App zum Tag
    # nichts, statt einen freien Tag zu behaupten.
    tagestyp: str | None = None
    tagestyp_hinweis: str | None = None
    # An einem Feiertag oder im Urlaub bleibt derselbe Trainingstag stehen,
    # gilt aber nicht als selbstverstaendlich. Der Plan wird bewusst nicht
    # ausgetauscht: eine App, die ihn hinter dem Ruecken des Nutzers umbaut,
    # ist schwerer zu durchschauen als eine, die eine Zeile dazu sagt.
    vorschlag_optional: bool = False


# ---------------------------------------------------------------------------
# Muscle Freshness & Recommendations
# ---------------------------------------------------------------------------

class MuscleGroupFreshness(BaseModel):
    region: str
    label: str
    days_since_trained: int | None = None
    color: str
    total_volume_last: float = 0
    exercises_available: int = 0


class MuscleFreshnessResponse(BaseModel):
    regions: list[MuscleGroupFreshness]
    workouts_this_week: int = 0
    current_streak: int = 0


class ExerciseRecommendation(BaseModel):
    exercise_id: int
    exercise_name: str
    category: str
    primary_muscles: list[str]
    is_compound: bool
    reason: str
    priority_score: float


class RecommendationsResponse(BaseModel):
    recommendations: list[ExerciseRecommendation]
    muscle_balance: dict[str, float]


# ---------------------------------------------------------------------------
# Personal Records
# ---------------------------------------------------------------------------

class PersonalRecordOut(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str = ""
    pr_type: str
    value: float
    achieved_at: UtcDatetime
    workout_set_id: int | None

    model_config = {"from_attributes": True}


class PRCheckResult(BaseModel):
    new_prs: list[PersonalRecordOut] = []


# ---------------------------------------------------------------------------
# Exercise History
# ---------------------------------------------------------------------------

class ExerciseHistorySession(BaseModel):
    date: date
    workout_id: int
    workout_name: str
    sets: list[WorkoutSetOut]


# ---------------------------------------------------------------------------
# Workout Suggestions
# ---------------------------------------------------------------------------

class OverloadSuggestion(BaseModel):
    exercise_id: int
    exercise_name: str
    suggested_weight_kg: float | None = None
    suggested_reps: int | None = None
    last_weight_kg: float | None = None
    last_reps: int | None = None
    reason: str = ""


class LastWeightEntry(BaseModel):
    exercise_id: int
    weight_kg: float | None = None
    reps: int | None = None
    set_type: str = "normal"


# ---------------------------------------------------------------------------
# Volume per Muscle Group
# ---------------------------------------------------------------------------

class MuscleVolumeWeek(BaseModel):
    region: str
    label: str
    sets: int
    volume: float


class MuscleVolumeResponse(BaseModel):
    weeks: list[dict]  # list of {week_start, muscles: list[MuscleVolumeWeek]}


# ---------------------------------------------------------------------------
# Calendar Heatmap
# ---------------------------------------------------------------------------

class CalendarDay(BaseModel):
    date: date
    workouts: int
    sets: int


# ---------------------------------------------------------------------------
# Strength Standards
# ---------------------------------------------------------------------------

class StrengthLevelOut(BaseModel):
    exercise_id: int
    exercise_name: str
    current_1rm: float | None = None
    body_weight: float | None = None
    ratio: float | None = None
    level: str = "unbekannt"
    levels: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Readiness Analytics
# ---------------------------------------------------------------------------

class ReadinessDayAverage(BaseModel):
    date: date
    avg_fatigue: float
    avg_sleep: float
    avg_motivation: float
    workout_count: int


class ReadinessCorrelation(BaseModel):
    high_avg_volume: float | None = None
    low_avg_volume: float | None = None
    high_workout_count: int = 0
    low_workout_count: int = 0


class ReadinessAnalyticsResponse(BaseModel):
    daily_averages: list[ReadinessDayAverage]
    sleep_correlation: ReadinessCorrelation
    fatigue_correlation: ReadinessCorrelation
    workouts_with_readiness: int
    workouts_without_readiness: int


# ---------------------------------------------------------------------------
# Nutzerprofil und Ausruestung
# ---------------------------------------------------------------------------

class ProfilUpdate(BaseModel):
    geraete: list[str] | None = None
    erfahrung: str | None = None
    ziel: str | None = None
    trainingstage_pro_woche: int | None = Field(None, ge=1, le=7)
    gewichtsschritt_kg: float | None = Field(None, gt=0, le=25)
    kurzhantel_max_kg: float | None = Field(None, ge=0, le=200)
    koerpergewicht_kg: float | None = Field(None, gt=20, le=350)
    koerpergroesse_cm: float | None = Field(None, gt=80, le=250)
    geburtsjahr: int | None = Field(None, ge=1900, le=2030)
    geschlecht: str | None = None
    einschraenkungen: list[str] | None = None


class ProfilOut(BaseModel):
    geraete: list[str]
    eingerichtet: bool
    erfahrung: str
    ziel: str
    trainingstage_pro_woche: int
    gewichtsschritt_kg: float
    kurzhantel_max_kg: float | None
    koerpergewicht_kg: float | None
    koerpergroesse_cm: float | None
    geburtsjahr: int | None
    geschlecht: str
    einschraenkungen: list[str]
    zielbereich_wdh: list[int]


class GeraetOut(BaseModel):
    id: str
    name: str
    ersatz: list[str] = []
    ersatz_namen: list[str] = []
    hinweis: str = ""


class VorlageOut(BaseModel):
    id: str
    name: str
    beschreibung: str
    geraete: list[str]


class AusruestungslueckeOut(BaseModel):
    exercise_id: int
    name: str
    fehlt: list[str]
    fehlt_namen: list[str]
    mit_ersatz: bool
    ersatz_namen: list[str]


# ---------------------------------------------------------------------------
# Muskel-Registry
# ---------------------------------------------------------------------------

class MuskelgruppeOut(BaseModel):
    id: str
    name: str
    region: str
    ppl: str
    mv: int
    mev: int
    mav_min: int
    mav_max: int
    mrv: int
    erholung_stunden: int


class MuskelOut(BaseModel):
    id: str
    name: str
    fachname: str
    gruppe: str
    ansicht: str
    funktion: str = ""


class RegistryOut(BaseModel):
    regionen: list[dict]
    gruppen: list[MuskelgruppeOut]
    muskeln: list[MuskelOut]


# ---------------------------------------------------------------------------
# Volumen, Frische, Empfehlung
# ---------------------------------------------------------------------------

class GruppenwocheOut(BaseModel):
    gruppe: str
    name: str
    region: str
    direkt: float
    gewichtet: float
    volumen_kg: float
    bewertung: str
    mv: int
    mev: int
    mav_min: int
    mav_max: int
    mrv: int
    hinweis: str


class GruppenfrischeOut(BaseModel):
    gruppe: str
    name: str
    region: str
    stunden_seit: float | None
    frische: float
    bereit_in_stunden: float
    letzte_saetze: float


class MuskelstandOut(BaseModel):
    saetze: float
    volumen_kg: float
    tage_seit: int | None


class UebungsvorschlagOut(BaseModel):
    exercise_id: int
    name: str
    kategorie: str
    equipment: str
    gruppe: str
    gruppenname: str
    grunduebung: bool
    anteil: float
    punkte: float
    begruendung: str
    gewicht_kg: float | None = None
    wdh: int | None = None
    saetze: int = 3
    pause_s: int = 90


class GruppenempfehlungOut(BaseModel):
    gruppe: str
    name: str
    region: str
    punkte: float
    bedarf: float
    frische: float
    begruendung: str
    uebungen: list[UebungsvorschlagOut] = []


class EinheitsvorschlagOut(BaseModel):
    dauer_minuten: int
    geplante_minuten: int
    gruppen: list[str]
    uebungen: list[UebungsvorschlagOut] = []


class JetztUebungOut(BaseModel):
    exercise_id: int
    name: str
    kategorie: str
    equipment: str
    gruppenname: str
    saetze: int
    pause_s: int
    wdh: int | None = None
    gewicht_kg: float | None = None
    begruendung: str = ""
    gekuerzt_von: int | None = None
    ergaenzt: bool = False


class TrainingJetztOut(BaseModel):
    """Was jetzt trainiert wird, in der Zeit, die da ist.

    ★ ``minuten_quelle`` gehoert in die Antwort und nicht in ein Protokoll:
    ``kalender`` heisst gemessen, ``vorgabe`` heisst geraten. Ohne die
    Unterscheidung sieht eine Vorgabe von 45 Minuten genauso aus wie ein
    echter Trainingsblock, und die Oberflaeche kann nicht sagen, worauf der
    Zuschnitt beruht.
    """

    minuten: int
    minuten_quelle: str
    quelle: str
    titel: str
    begruendung: str
    geplante_minuten: int
    uebungen: list[JetztUebungOut] = []
    gruppen: list[str] = []
    plantag: str | None = None
    plantag_id: int | None = None
    hinweise: list[str] = []


class ProgressionsvorschlagOut(BaseModel):
    exercise_id: int
    exercise_name: str
    gewicht_kg: float | None = None
    wdh: int | None = None
    letztes_gewicht_kg: float | None = None
    letzte_wdh: int | None = None
    art: str
    begruendung: str
    zielbereich: list[int]
    e1rm: float | None = None
    e1rm_unsicher: bool = False
    plateau_seit: int = 0
    aufwaermsaetze: list[dict] = []


# ---------------------------------------------------------------------------
# Schritte
# ---------------------------------------------------------------------------

class SchritteEintrag(BaseModel):
    datum: date
    schritte: int = Field(..., ge=0, le=200000)
    distanz_m: float | None = Field(None, ge=0)
    aktive_kcal: float | None = Field(None, ge=0)
    quelle: str = "manuell"


class SchritteOut(BaseModel):
    datum: date
    schritte: int
    distanz_m: float | None = None
    aktive_kcal: float | None = None
    quelle: str = "manuell"

    model_config = {"from_attributes": True}


class SchritteUebersichtOut(BaseModel):
    tage: list[SchritteOut]
    heute: int | None = None
    schnitt: int | None = None
    aktive_tage: int = 0
    erfasste_tage: int = 0


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

class AchievementOut(BaseModel):
    id: int
    key: str
    name: str
    description: str | None
    icon: str | None
    category: str | None
    unlocked_at: UtcDatetime | None = None

    model_config = {"from_attributes": True}
