export interface Exercise {
  id: number;
  name: string;
  category: string;
  equipment: string;
  primary_muscles: string[];
  secondary_muscles: string[];
  is_compound: boolean;
  is_selected: boolean;
  notes: string | null;
  /** Selbst angelegt (aenderbar) oder Teil des gemeinsamen Katalogs. */
  is_eigene?: boolean;

  /** Muskelkennung auf Anteil zwischen 0 und 1. Trägt Modell und Auswahl. */
  muskel_anteile?: Record<string, number>;
  /** Gerätekennungen, ohne die die Übung nicht geht. */
  benoetigt?: string[];
  muster?: string | null;
  /** Anteil des Körpergewichts, den die Übung bewegt. 0 = Hantelübung. */
  kg_anteil?: number;
  griff?: string | null;
  reihe?: string | null;
  stufe?: number;
  einseitig?: boolean;
  ist_zeit?: boolean;
  wdh_min?: number;
  wdh_max?: number;
  pause_s?: number;
  ausfuehrung?: string | null;
  fehler?: string | null;
  /** Mit der eingetragenen Ausrüstung machbar. */
  machbar: boolean;
  fehlt_namen: string[];
}

/* --- Muskel-Registry ------------------------------------------------ */

export interface Muskelgruppe {
  id: string;
  name: string;
  region: string;
  ppl: string;
  mv: number;
  mev: number;
  mav_min: number;
  mav_max: number;
  mrv: number;
  erholung_stunden: number;
}

export interface Muskel {
  id: string;
  name: string;
  fachname: string;
  gruppe: string;
  ansicht: string;
  funktion: string;
}

export interface Registry {
  regionen: { id: string; name: string }[];
  gruppen: Muskelgruppe[];
  muskeln: Muskel[];
}

export interface Muskelstand {
  saetze: number;
  volumen_kg: number;
  tage_seit: number | null;
}

export interface Gruppenwoche {
  gruppe: string;
  name: string;
  region: string;
  direkt: number;
  gewichtet: number;
  volumen_kg: number;
  bewertung: 'unter_mv' | 'erhaltung' | 'unter_mev' | 'im_korridor'
           | 'ueber_mav' | 'ueber_mrv';
  mv: number;
  mev: number;
  mav_min: number;
  mav_max: number;
  mrv: number;
  hinweis: string;
}

export interface Gruppenfrische {
  gruppe: string;
  name: string;
  region: string;
  stunden_seit: number | null;
  frische: number;
  bereit_in_stunden: number;
  letzte_saetze: number;
}

/* --- Profil und Ausrüstung ----------------------------------------- */

export interface Profil {
  geraete: string[];
  eingerichtet: boolean;
  erfahrung: string;
  ziel: string;
  trainingstage_pro_woche: number;
  gewichtsschritt_kg: number;
  kurzhantel_max_kg: number | null;
  koerpergewicht_kg: number | null;
  koerpergroesse_cm: number | null;
  geburtsjahr: number | null;
  geschlecht: string;
  einschraenkungen: string[];
  zielbereich_wdh: number[];
}

export interface Geraet {
  id: string;
  name: string;
  ersatz: string[];
  ersatz_namen: string[];
  hinweis: string;
}

export interface Vorlage {
  id: string;
  name: string;
  beschreibung: string;
  geraete: string[];
}

export interface Ausruestungsluecke {
  exercise_id: number;
  name: string;
  fehlt: string[];
  fehlt_namen: string[];
  mit_ersatz: boolean;
  ersatz_namen: string[];
}

/* --- Empfehlung und Progression ------------------------------------ */

export interface Uebungsvorschlag {
  exercise_id: number;
  name: string;
  kategorie: string;
  equipment: string;
  gruppe: string;
  gruppenname: string;
  grunduebung: boolean;
  anteil: number;
  punkte: number;
  begruendung: string;
  gewicht_kg: number | null;
  wdh: number | null;
  saetze: number;
  pause_s: number;
}

export interface Gruppenempfehlung {
  gruppe: string;
  name: string;
  region: string;
  punkte: number;
  bedarf: number;
  frische: number;
  begruendung: string;
  uebungen: Uebungsvorschlag[];
}

export interface Einheitsvorschlag {
  dauer_minuten: number;
  geplante_minuten: number;
  gruppen: string[];
  uebungen: Uebungsvorschlag[];
}

export interface Progressionsvorschlag {
  exercise_id: number;
  exercise_name: string;
  gewicht_kg: number | null;
  wdh: number | null;
  letztes_gewicht_kg: number | null;
  letzte_wdh: number | null;
  art: 'steigern' | 'wiederholen' | 'wdh_steigern' | 'reduzieren'
     | 'einstieg' | 'plateau';
  begruendung: string;
  zielbereich: number[];
  e1rm: number | null;
  e1rm_unsicher: boolean;
  plateau_seit: number;
  aufwaermsaetze: { gewicht_kg: number; wdh: number; anteil: number }[];
}

/* --- Schritte -------------------------------------------------------- */

export interface Schritttag {
  datum: string;
  schritte: number;
  distanz_m: number | null;
  aktive_kcal: number | null;
  quelle: string;
}

export interface Schritteuebersicht {
  tage: Schritttag[];
  heute: number | null;
  schnitt: number | null;
  aktive_tage: number;
  erfasste_tage: number;
}

export interface PlanExercise {
  id: number;
  exercise_id: number;
  exercise_name: string;
  sort_order: number;
  target_sets: number;
  target_reps_min: number;
  target_reps_max: number;
  target_rpe: number | null;
  rest_seconds: number;
  notes: string | null;
}

export interface PlanDay {
  id: number;
  name: string;
  day_of_week: number | null;
  sort_order: number;
  exercises: PlanExercise[];
}

export interface Plan {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  days: PlanDay[];
}

export interface PlanListItem {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  day_count: number;
}

export interface Planvorlage {
  id: string;
  name: string;
  beschreibung: string;
  tage_pro_woche: number;
  /** Deckt sich mit den eingestellten Trainingstagen. */
  passt: boolean;
}

export interface WorkoutSet {
  id: number;
  exercise_id: number;
  exercise_name: string;
  set_number: number;
  weight_kg: number | null;
  reps: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  rpe: number | null;
  is_warmup: boolean;
  set_type: string;
  group_id: string | null;
  notes: string | null;
  /** Abgehakt oder nur geplant. Vorbefuellte Saetze aus dem Plan sind false. */
  is_completed: boolean;
  completed_at: string | null;
}

export interface PlanTarget {
  exercise_id: number;
  exercise_name: string;
  target_sets: number;
  target_reps_min: number;
  target_reps_max: number;
  target_rpe: number | null;
  rest_seconds: number;
  notes: string | null;
}

export interface Workout {
  id: number;
  plan_day_id: number | null;
  plan_day_name: string | null;
  name: string;
  started_at: string;
  finished_at: string | null;
  notes: string | null;
  rating: number | null;
  fatigue_level: number | null;
  sleep_quality: number | null;
  motivation: number | null;
  pre_notes: string | null;
  sets: WorkoutSet[];
  /** Vorgaben des Trainingstages, leer bei freiem Training. */
  plan_targets: PlanTarget[];
}

export interface WorkoutListItem {
  id: number;
  name: string;
  started_at: string;
  finished_at: string | null;
  rating: number | null;
  set_count: number;
}

export interface BodyMetric {
  id: number;
  date: string;
  weight_kg: number;
  body_fat_pct: number | null;
  waist_cm: number | null;
  notes: string | null;
}

/** Aktivitaetsniveau aus dem tatsaechlichen Training. Eingangsgroesse fuer
 *  MealPreps Tagesbedarf. */
export interface Aktivitaetsniveau {
  stufe: string;
  faktor: number;
  begruendung: string;
  trainings_pro_woche: number;
  trainings_im_fenster: number;
  fenster_tage: number;
  an_mealprep_uebertragen: boolean;
  /** Genug erfasst, um daraus einen Bedarf abzuleiten. */
  belastbar: boolean;
}

/** Tagesziele aus MealPrep. verfuegbar=false heisst: Dienst nicht erreichbar. */
export interface MealprepZiele {
  verfuegbar: boolean;
  kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
}

export interface BodyTrendPoint {
  date: string;
  weight_kg: number;
  moving_avg: number | null;
}

export interface ExerciseProgressPoint {
  date: string;
  estimated_1rm: number | null;
  best_set_weight: number | null;
  best_set_reps: number | null;
  total_volume: number;
}

export interface VolumeSummary {
  week_start: string;
  total_volume: number;
  total_sets: number;
  workouts: number;
}

export interface DashboardSummary {
  workouts_7d: number;
  workouts_30d: number;
  total_volume_7d: number;
  current_streak: number;
  last_workout: string | null;
  /** Trainingstag, der ansteht: fester Wochentag, sonst Rotation. */
  next_plan_day: string | null;
  next_plan_day_id: number | null;
  /** Tagestyp aus dem Kalender. null heisst "nicht gemessen", nicht "frei". */
  tagestyp: string | null;
  tagestyp_hinweis: string | null;
  /** Feiertag oder Urlaub: der Plan bleibt stehen, gilt aber nicht als Muss. */
  vorschlag_optional: boolean;
}

export interface MuscleGroupFreshness {
  region: string;
  label: string;
  days_since_trained: number | null;
  color: string;
  total_volume_last: number;
  exercises_available: number;
}

export interface MuscleFreshnessResponse {
  regions: MuscleGroupFreshness[];
  workouts_this_week: number;
  current_streak: number;
}

export interface ExerciseRecommendation {
  exercise_id: number;
  exercise_name: string;
  category: string;
  primary_muscles: string[];
  is_compound: boolean;
  reason: string;
  priority_score: number;
}

export interface RecommendationsResponse {
  recommendations: ExerciseRecommendation[];
  muscle_balance: Record<string, number>;
}

// Personal Records
export interface PersonalRecord {
  id: number;
  exercise_id: number;
  exercise_name: string;
  pr_type: string;
  value: number;
  achieved_at: string;
  workout_set_id: number | null;
}

// Exercise History
export interface ExerciseHistorySession {
  date: string;
  workout_id: number;
  workout_name: string;
  sets: WorkoutSet[];
}

// Overload Suggestion
export interface OverloadSuggestion {
  exercise_id: number;
  exercise_name: string;
  suggested_weight_kg: number | null;
  suggested_reps: number | null;
  last_weight_kg: number | null;
  last_reps: number | null;
  reason: string;
}

// Last Weight Entry
export interface LastWeightEntry {
  exercise_id: number;
  weight_kg: number | null;
  reps: number | null;
  set_type: string;
}

// Volume per Muscle Group
export interface MuscleVolumeWeek {
  region: string;
  label: string;
  sets: number;
  volume: number;
}

export interface MuscleVolumeResponse {
  weeks: { week_start: string; muscles: MuscleVolumeWeek[] }[];
}

// Calendar Heatmap
export interface CalendarDay {
  date: string;
  workouts: number;
  sets: number;
}

// Strength Standards
export interface StrengthLevel {
  exercise_id: number;
  exercise_name: string;
  current_1rm: number | null;
  body_weight: number | null;
  ratio: number | null;
  level: string;
  levels: Record<string, number>;
}

// Readiness Analytics
export interface ReadinessDayAverage {
  date: string;
  avg_fatigue: number;
  avg_sleep: number;
  avg_motivation: number;
  workout_count: number;
}

export interface ReadinessCorrelation {
  high_avg_volume: number | null;
  low_avg_volume: number | null;
  high_workout_count: number;
  low_workout_count: number;
}

export interface ReadinessAnalyticsResponse {
  daily_averages: ReadinessDayAverage[];
  sleep_correlation: ReadinessCorrelation;
  fatigue_correlation: ReadinessCorrelation;
  workouts_with_readiness: number;
  workouts_without_readiness: number;
}

// Achievements
export interface Achievement {
  id: number;
  key: string;
  name: string;
  description: string | null;
  icon: string | null;
  category: string | null;
  unlocked_at: string | null;
}
