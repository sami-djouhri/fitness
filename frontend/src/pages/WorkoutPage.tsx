import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../api';
import type { Workout, WorkoutSet, Exercise, PlanListItem, Plan, OverloadSuggestion, LastWeightEntry, MuscleFreshnessResponse, PlanTarget } from '../types';
import { aufIdAufloesung } from '../warteschlange';
import ExercisePicker from '../components/ExercisePicker';
import SetRow from '../components/SetRow';
import RestTimer from '../components/RestTimer';
import ReadinessCheck from '../components/ReadinessCheck';

const SET_TYPES = [
  { value: 'normal', label: 'Normal' },
  { value: 'warmup', label: 'Warmup' },
  { value: 'dropset', label: 'Dropset' },
  { value: 'failure', label: 'Failure' },
  { value: 'rest_pause', label: 'Rest-Pause' },
];

export default function WorkoutPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [workout, setWorkout] = useState<Workout | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [plans, setPlans] = useState<PlanListItem[]>([]);
  const [restTimer, setRestTimer] = useState<{ seconds: number } | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [lastWeights, setLastWeights] = useState<Record<number, LastWeightEntry>>({});
  const [suggestions, setSuggestions] = useState<Record<number, OverloadSuggestion>>({});
  const [ratingValue, setRatingValue] = useState(0);
  const [showRating, setShowRating] = useState(false);
  const [recRegion, setRecRegion] = useState<string | null>(null);
  const [pendingWorkout, setPendingWorkout] = useState<{ plan_day_id?: number; name?: string; exercise_ids?: number[] } | null>(null);
  const [namensAbfrage, setNamensAbfrage] = useState<string | null>(null);
  const [startingWorkout, setStartingWorkout] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const isNew = !id;

  // Pick up pending workout info from navigation state (e.g. from TodayTraining / DashboardPage)
  useEffect(() => {
    const state = location.state as { pendingName?: string; pendingPlanDayId?: number; pendingExerciseIds?: number[] } | null;
    if (state && !id) {
      if (state.pendingName || state.pendingPlanDayId || state.pendingExerciseIds) {
        setPendingWorkout({
          name: state.pendingName,
          plan_day_id: state.pendingPlanDayId,
          exercise_ids: state.pendingExerciseIds,
        });
        // Clear the navigation state so it doesn't re-trigger
        window.history.replaceState({}, '');
      }
    }
  }, [location.state, id]);

  useEffect(() => {
    if (id) {
      loadWorkout(parseInt(id));
    } else {
      api.get<PlanListItem[]>('/plans').then(setPlans);
      // Load recommended region for quick-start
      api.get<MuscleFreshnessResponse>('/progress/muscle-freshness')
        .then(f => {
          const best = f.regions
            .filter(r => r.exercises_available > 0)
            .sort((a, b) => {
              const aDays = a.days_since_trained ?? 999;
              const bDays = b.days_since_trained ?? 999;
              return bDays - aDays;
            })[0];
          if (best) setRecRegion(best.label);
        })
        .catch(() => {});
    }
  }, [id]);

  // Workout elapsed timer
  useEffect(() => {
    if (workout && !workout.finished_at) {
      const start = new Date(workout.started_at).getTime();
      const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
      tick();
      timerRef.current = setInterval(tick, 1000);
      return () => clearInterval(timerRef.current);
    }
  }, [workout?.id, workout?.finished_at]);

  /**
   * Bildschirm wach halten, solange die Session laeuft. Sonst sperrt das
   * Handy zwischen zwei Saetzen, und man entsperrt es mit nassen Haenden.
   * Wake Lock gibt es nur im sicheren Kontext und nicht in jedem Browser,
   * deshalb durchgehend fehlertolerant.
   */
  useEffect(() => {
    if (!workout || workout.finished_at) return;
    let sperre: WakeLockSentinel | null = null;
    let aufgeraeumt = false;

    const anfordern = async () => {
      try {
        const nav = navigator as Navigator & { wakeLock?: { request: (typ: 'screen') => Promise<WakeLockSentinel> } };
        if (!nav.wakeLock || aufgeraeumt) return;
        sperre = await nav.wakeLock.request('screen');
      } catch {
        // Kein Wake Lock verfuegbar. Die Session laeuft normal weiter.
      }
    };

    // Nach dem Zurueckkehren erneut anfordern: der Browser gibt die Sperre
    // beim Wechsel in den Hintergrund von selbst frei.
    const beiSichtwechsel = () => {
      if (document.visibilityState === 'visible') void anfordern();
    };

    void anfordern();
    document.addEventListener('visibilitychange', beiSichtwechsel);
    return () => {
      aufgeraeumt = true;
      document.removeEventListener('visibilitychange', beiSichtwechsel);
      void sperre?.release().catch(() => {});
    };
  }, [workout?.id, workout?.finished_at]);

  /**
   * Nachgetragene Saetze bekommen ihre echte Nummer. Ohne das zeigt die
   * Oberflaeche nach einem Netzausfall weiter die Ersatznummer, und die
   * naechste Aenderung an diesem Satz ginge an eine Adresse, die es nicht gibt.
   */
  useEffect(() => aufIdAufloesung((ersatzId, echteId) => {
    setWorkout(prev => prev
      ? { ...prev, sets: prev.sets.map(s => s.id === ersatzId ? { ...s, id: echteId } : s) }
      : prev);
  }), []);

  async function loadWorkout(wid: number) {
    const w = await api.get<Workout>(`/workouts/${wid}`);
    setWorkout(w);

    // Load last weights for exercises in this workout
    const exerciseIds = [...new Set(w.sets.map(s => s.exercise_id))];
    if (exerciseIds.length > 0) {
      const lw = await api.get<LastWeightEntry[]>(`/workouts/last-weights?exercise_ids=${exerciseIds.join(',')}`);
      const map: Record<number, LastWeightEntry> = {};
      for (const entry of lw) map[entry.exercise_id] = entry;
      setLastWeights(map);
    }
  }

  async function loadSuggestion(exerciseId: number) {
    if (suggestions[exerciseId]) return;
    const s = await api.get<OverloadSuggestion>(`/workouts/suggestions?exercise_id=${exerciseId}`);
    setSuggestions(prev => ({ ...prev, [exerciseId]: s }));
  }

  function startWorkout(planDayId?: number) {
    setPendingWorkout({ plan_day_id: planDayId });
  }

  function startFreeWorkout() {
    // Kein prompt(): der Systemdialog blockiert die Seite, sieht in einer
    // installierten Web-App fremd aus und wird auf iOS teils unterdrueckt.
    setNamensAbfrage('Freies Training');
  }

  function startRecWorkout() {
    if (!recRegion) return;
    setPendingWorkout({ name: `${recRegion} Training` });
  }

  /** Einmal fragen, damit die Pausen-Meldung zustellbar ist. */
  function meldungErlauben() {
    try {
      if ('Notification' in window && Notification.permission === 'default') {
        void Notification.requestPermission();
      }
    } catch {
      // Nicht jede Umgebung erlaubt das. Der Timer vibriert dann nur.
    }
  }

  async function createWorkoutWithReadiness(readinessData: {
    fatigue_level: number | null;
    sleep_quality: number | null;
    motivation: number | null;
    pre_notes: string;
  }) {
    if (!pendingWorkout) return;
    setStartingWorkout(true);
    meldungErlauben();
    try {
      const w = await api.post<Workout>('/workouts', {
        plan_day_id: pendingWorkout.plan_day_id ?? null,
        name: pendingWorkout.name,
        exercise_ids: pendingWorkout.exercise_ids ?? null,
        fatigue_level: readinessData.fatigue_level,
        sleep_quality: readinessData.sleep_quality,
        motivation: readinessData.motivation,
        pre_notes: readinessData.pre_notes || null,
      });
      navigate(`/workout/${w.id}`, { replace: true });
    } finally {
      setStartingWorkout(false);
    }
  }

  async function skipReadinessCheck() {
    if (!pendingWorkout) return;
    setStartingWorkout(true);
    try {
      const w = await api.post<Workout>('/workouts', {
        plan_day_id: pendingWorkout.plan_day_id ?? null,
        name: pendingWorkout.name,
        exercise_ids: pendingWorkout.exercise_ids ?? null,
      });
      navigate(`/workout/${w.id}`, { replace: true });
    } finally {
      setStartingWorkout(false);
    }
  }

  async function addSet(exerciseId: number, setType: string = 'normal', groupId?: string) {
    if (!workout) return;
    const exerciseSets = workout.sets.filter(s => s.exercise_id === exerciseId);
    const nextNum = exerciseSets.length + 1;
    const lastSet = exerciseSets[exerciseSets.length - 1];

    let weight = lastSet?.weight_kg ?? lastWeights[exerciseId]?.weight_kg ?? null;
    let reps = lastSet?.reps ?? lastWeights[exerciseId]?.reps ?? null;

    const sug = suggestions[exerciseId];
    if (!lastSet && sug?.suggested_weight_kg) {
      weight = sug.suggested_weight_kg;
      reps = sug.suggested_reps;
    }

    const rumpf = {
      exercise_id: exerciseId,
      set_number: nextNum,
      weight_kg: weight,
      reps: reps,
      set_type: setType,
      is_warmup: setType === 'warmup',
      group_id: groupId ?? null,
    };

    // Kein Neuaufbau der ganzen Session nach jedem Satz mehr: der Satz steht
    // sofort da, die Uebertragung laeuft daneben. Bei Netzausfall vergibt die
    // Warteschlange eine Ersatznummer und traegt spaeter nach.
    const neuerSatz = await api.postRobust<WorkoutSet>(
      `/workouts/${workout.id}/sets`,
      rumpf,
      ersatzId => ({
        id: ersatzId,
        exercise_id: exerciseId,
        exercise_name: exerciseSets[0]?.exercise_name
          ?? workout.plan_targets.find(v => v.exercise_id === exerciseId)?.exercise_name
          ?? '',
        set_number: nextNum,
        weight_kg: weight,
        reps: reps,
        duration_seconds: null,
        distance_meters: null,
        rpe: null,
        is_warmup: setType === 'warmup',
        set_type: setType,
        group_id: groupId ?? null,
        notes: null,
        is_completed: true,
        completed_at: null,
      }),
    );
    satzEinfuegen(neuerSatz);

    if (setType !== 'warmup') {
      setRestTimer({ seconds: pauseFuer(exerciseId) });
    }
  }

  function vorgabeFuer(exerciseId: number): PlanTarget | undefined {
    return workout?.plan_targets.find(v => v.exercise_id === exerciseId);
  }

  /** "3 Saetze, 6 bis 10 Wdh, Pause 2:00" als eine Zeile unter dem Namen. */
  function vorgabeText(exerciseId: number): string {
    const v = vorgabeFuer(exerciseId);
    if (!v) return '';
    const teile = [`${v.target_sets} S\u00e4tze`];
    teile.push(v.target_reps_min === v.target_reps_max
      ? `${v.target_reps_min} Wdh`
      : `${v.target_reps_min} bis ${v.target_reps_max} Wdh`);
    if (v.target_rpe) teile.push(`RPE ${v.target_rpe}`);
    const min = Math.floor(v.rest_seconds / 60);
    const sek = v.rest_seconds % 60;
    teile.push(`Pause ${min}:${String(sek).padStart(2, '0')}`);
    return teile.join(', ');
  }

  function zielRepsText(exerciseId: number): string | undefined {
    const v = vorgabeFuer(exerciseId);
    if (!v) return undefined;
    return v.target_reps_min === v.target_reps_max
      ? `${v.target_reps_min}`
      : `${v.target_reps_min}-${v.target_reps_max}`;
  }

  /** Pause aus dem Plan, sonst die bisherige Vorgabe von 90 Sekunden. */
  function pauseFuer(exerciseId: number): number {
    const vorgabe = workout?.plan_targets.find(v => v.exercise_id === exerciseId);
    return vorgabe?.rest_seconds ?? 90;
  }

  function satzEinfuegen(satz: WorkoutSet) {
    setWorkout(prev => prev ? { ...prev, sets: [...prev.sets, satz] } : prev);
  }

  function satzAendern(setId: number, aenderung: Partial<WorkoutSet>) {
    setWorkout(prev => prev
      ? { ...prev, sets: prev.sets.map(s => s.id === setId ? { ...s, ...aenderung } : s) }
      : prev);
  }

  /** Abhaken ist der Schritt, mit dem ein geplanter Satz ein gemachter wird. */
  async function satzAbhaken(satz: WorkoutSet) {
    const jetztErledigt = !satz.is_completed;
    satzAendern(satz.id, {
      is_completed: jetztErledigt,
      completed_at: jetztErledigt ? new Date().toISOString() : null,
    });
    await api.putRobust(`/workouts/sets/${satz.id}`, { is_completed: jetztErledigt });
    if (jetztErledigt && !satz.is_warmup) {
      setRestTimer({ seconds: pauseFuer(satz.exercise_id) });
    }
  }

  async function toggleSuperset(exerciseIdA: number, exerciseIdB: number) {
    if (!workout) return;
    const setsA = workout.sets.filter(s => s.exercise_id === exerciseIdA);
    const setsB = workout.sets.filter(s => s.exercise_id === exerciseIdB);
    const existingGroup = setsA[0]?.group_id;

    const aufloesen = existingGroup && setsB.some(s => s.group_id === existingGroup);
    const gid = aufloesen ? null : `ss-${Date.now()}`;
    for (const s of [...setsA, ...setsB]) {
      satzAendern(s.id, { group_id: gid });
      await api.putRobust(`/workouts/sets/${s.id}`, { group_id: gid });
    }
  }

  async function deleteSet(setId: number) {
    setWorkout(prev => prev ? { ...prev, sets: prev.sets.filter(s => s.id !== setId) } : prev);
    await api.delRobust(`/workouts/sets/${setId}`);
  }

  async function finishWorkout() {
    if (!workout) return;
    await api.post(`/workouts/${workout.id}/finish`);
    setShowRating(true);
  }

  async function submitRating(rating: number) {
    if (!workout) return;
    await api.put(`/workouts/${workout.id}`, { rating });
    api.post('/achievements/check').catch(() => {});
    navigate('/');
  }

  async function skipRating() {
    api.post('/achievements/check').catch(() => {});
    navigate('/');
  }

  async function onExerciseSelected(ex: Exercise) {
    setShowPicker(false);
    if (workout) {
      loadSuggestion(ex.id);
      addSet(ex.id);
    }
  }

  function formatElapsed(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  // Rating overlay
  if (showRating) {
    return (
      <div className="page fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <h2 style={{ marginBottom: 16, color: 'var(--text)' }}>Wie war das Training?</h2>
        <div className="star-rating" style={{ marginBottom: 24 }}>
          {[1, 2, 3, 4, 5].map(star => (
            <button
              key={star}
              className={`star-rating-btn ${star <= ratingValue ? 'active' : ''}`}
              onClick={() => setRatingValue(star)}
            >
              ★
            </button>
          ))}
        </div>
        <button
          className="btn-primary"
          style={{ width: '100%', maxWidth: 300, marginBottom: 8 }}
          onClick={() => submitRating(ratingValue)}
          disabled={ratingValue === 0}
        >
          Bewerten
        </button>
        <button
          className="btn-secondary"
          style={{ width: '100%', maxWidth: 300 }}
          onClick={skipRating}
        >
          Überspringen
        </button>
      </div>
    );
  }

  // Namensabfrage fuer das freie Training, als Bildschirm statt Systemdialog.
  if (isNew && !workout && namensAbfrage !== null) {
    return (
      <div className="page fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <button className="btn-secondary btn-sm" onClick={() => setNamensAbfrage(null)}>&larr;</button>
          <h1 style={{ margin: 0 }}>Freies Training</h1>
        </div>
        <form
          onSubmit={e => {
            e.preventDefault();
            const name = namensAbfrage.trim();
            if (!name) return;
            setNamensAbfrage(null);
            setPendingWorkout({ name });
          }}
        >
          <input
            value={namensAbfrage}
            onChange={e => setNamensAbfrage(e.target.value)}
            placeholder="Name des Trainings"
            style={{ width: '100%', marginBottom: 12, fontSize: '1rem', padding: '12px' }}
            autoFocus
          />
          <button className="btn-primary" type="submit" style={{ width: '100%' }} disabled={!namensAbfrage.trim()}>
            Weiter
          </button>
        </form>
      </div>
    );
  }

  // Readiness check screen
  if (isNew && !workout && pendingWorkout) {
    return (
      <div className="page fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <button
            className="btn-secondary btn-sm"
            onClick={() => setPendingWorkout(null)}
          >
            &larr;
          </button>
          <h1 style={{ margin: 0 }}>Vor dem Training</h1>
        </div>
        <ReadinessCheck
          onStart={createWorkoutWithReadiness}
          onSkip={skipReadinessCheck}
          loading={startingWorkout}
        />
      </div>
    );
  }

  // Start screen
  if (isNew && !workout) {
    const activePlan = plans.find(p => p.is_active);
    return (
      <div className="page fade-in">
        <h1>Workout starten</h1>

        {/* Recommended quick-start */}
        {recRegion && (
          <div className="card-hero" style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 4 }}>Empfohlen</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>{recRegion} Training</div>
            <button className="btn-primary" style={{ width: '100%' }} onClick={startRecWorkout}>
              Starten
            </button>
          </div>
        )}

        {activePlan && (
          <div className="mb-16">
            <h2>Aktiver Plan: {activePlan.name}</h2>
            <PlanDaySelector planId={activePlan.id} onSelect={startWorkout} />
          </div>
        )}

        <button className="btn-secondary" onClick={startFreeWorkout} style={{ width: '100%' }}>
          Freies Training starten
        </button>
      </div>
    );
  }

  if (!workout) return <div className="page fade-in">Laden...</div>;

  // Group sets by exercise
  const exerciseGroups: { exerciseId: number; name: string; sets: typeof workout.sets; groupId: string | null }[] = [];
  const seen = new Set<number>();
  for (const s of workout.sets) {
    if (!seen.has(s.exercise_id)) {
      seen.add(s.exercise_id);
      const exSets = workout.sets.filter(ss => ss.exercise_id === s.exercise_id);
      exerciseGroups.push({
        exerciseId: s.exercise_id,
        name: s.exercise_name,
        sets: exSets,
        groupId: exSets[0]?.group_id ?? null,
      });
    }
  }

  // Identify superset partners
  const supersetGroups: Record<string, number[]> = {};
  for (const g of exerciseGroups) {
    if (g.groupId) {
      if (!supersetGroups[g.groupId]) supersetGroups[g.groupId] = [];
      supersetGroups[g.groupId].push(g.exerciseId);
    }
  }

  const isActive = !workout.finished_at;

  return (
    <div className="page fade-in">
      <div className="flex-between mb-16">
        <div>
          <h1 style={{ margin: 0 }}>{workout.name}</h1>
          {isActive && (
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)', fontVariantNumeric: 'tabular-nums' }}>
              {formatElapsed(elapsed)}
            </div>
          )}
          {workout.finished_at && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {new Date(workout.started_at).toLocaleDateString('de-DE')}
              {workout.rating && ` · ${'★'.repeat(workout.rating)}${'☆'.repeat(5 - workout.rating)}`}
            </div>
          )}
        </div>
        {isActive && (
          <button className="btn-primary" onClick={finishWorkout}>Beenden</button>
        )}
      </div>

      {/* Pre-workout readiness data */}
      {(workout.fatigue_level || workout.sleep_quality || workout.motivation || workout.pre_notes) && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>
            Bereitschafts-Check
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: workout.pre_notes ? 8 : 0 }}>
            {workout.fatigue_level && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.1rem' }}>
                  {['\u{1F4AA}', '\u{1F60A}', '\u{1F610}', '\u{1F634}', '\u{1F635}'][workout.fatigue_level - 1]}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {['Frisch', 'Gut', 'Normal', 'Muede', 'Erschoepft'][workout.fatigue_level - 1]}
                </div>
              </div>
            )}
            {workout.sleep_quality && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.1rem' }}>
                  {['\u{1F62B}', '\u{1F615}', '\u{1F610}', '\u{1F60C}', '\u{1F31F}'][workout.sleep_quality - 1]}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Schlaf: {['Schlecht', 'Maessig', 'OK', 'Gut', 'Sehr gut'][workout.sleep_quality - 1]}
                </div>
              </div>
            )}
            {workout.motivation && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.1rem' }}>
                  {['\u{1F612}', '\u{1F614}', '\u{1F610}', '\u{1F642}', '\u{1F525}'][workout.motivation - 1]}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Motivation: {['Niedrig', 'Gering', 'Mittel', 'Hoch', 'Max'][workout.motivation - 1]}
                </div>
              </div>
            )}
          </div>
          {workout.pre_notes && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {workout.pre_notes}
            </div>
          )}
        </div>
      )}

      {exerciseGroups.map((g, gi) => {
        const sug = suggestions[g.exerciseId];
        const ssPartners = g.groupId ? (supersetGroups[g.groupId] || []).filter(id => id !== g.exerciseId) : [];
        const isInSuperset = ssPartners.length > 0;
        const ssPartnerName = isInSuperset ? exerciseGroups.find(eg => eg.exerciseId === ssPartners[0])?.name : null;

        return (
          <div
            key={g.exerciseId}
            className="card"
            style={isInSuperset ? { borderLeft: '3px solid var(--warning)', marginBottom: 4 } : undefined}
          >
            <div className="flex-between mb-8">
              <div>
                <strong>{g.name}</strong>
                {vorgabeFuer(g.exerciseId) && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {vorgabeText(g.exerciseId)}
                    {' \u00b7 '}
                    {g.sets.filter(s => s.is_completed).length}/{g.sets.length} erledigt
                  </div>
                )}
                {isInSuperset && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--warning)', fontWeight: 600 }}>
                    Supersatz mit {ssPartnerName}
                  </div>
                )}
              </div>
              {isActive && (
                <div style={{ display: 'flex', gap: 4 }}>
                  {exerciseGroups.length > 1 && (
                    <select
                      className="btn-secondary btn-sm"
                      aria-label="Supersatz mit einer anderen Übung"
                      style={{ fontSize: '0.9rem', padding: '0 2px', minHeight: 36, width: 44 }}
                      onChange={e => {
                        if (e.target.value) toggleSuperset(g.exerciseId, parseInt(e.target.value));
                        e.target.value = '';
                      }}
                      defaultValue=""
                      title="Supersatz"
                    >
                      <option value="" disabled>{'\u21c4'}</option>
                      {exerciseGroups
                        .filter(eg => eg.exerciseId !== g.exerciseId)
                        .map(eg => (
                          <option key={eg.exerciseId} value={eg.exerciseId}>
                            {ssPartners.includes(eg.exerciseId) ? '✕ ' : ''}{eg.name.slice(0, 15)}
                          </option>
                        ))}
                    </select>
                  )}
                  <select
                    className="btn-secondary btn-sm"
                    aria-label="Satz hinzufügen"
                    title="Satz hinzufügen"
                    style={{ fontSize: '1.1rem', padding: '0 2px', minHeight: 36, width: 44 }}
                    onChange={e => { if (e.target.value) addSet(g.exerciseId, e.target.value, g.groupId ?? undefined); e.target.value = ''; }}
                    defaultValue=""
                  >
                    <option value="" disabled>+</option>
                    {SET_TYPES.map(st => (
                      <option key={st.value} value={st.value}>{st.label}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Suggestion display */}
            {sug && sug.reason && (
              <div className="overload-suggestion" style={{ marginBottom: 8, padding: '8px 12px' }}>
                <div className="overload-values" style={{ marginBottom: 2 }}>
                  {sug.suggested_weight_kg && (
                    <div className="overload-value" style={{ fontSize: '1.1rem' }}>
                      {sug.suggested_weight_kg}<span className="unit"> kg</span>
                    </div>
                  )}
                  {sug.suggested_reps && (
                    <div className="overload-value" style={{ fontSize: '1.1rem' }}>
                      {sug.suggested_reps}<span className="unit"> Wdh</span>
                    </div>
                  )}
                </div>
                <div className="overload-reason">{sug.reason}</div>
              </div>
            )}

            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              <span style={{ width: 30, display: 'inline-block' }}>#</span>
              <span style={{ flex: 1 }}>Gewicht</span>
              <span style={{ flex: 1, marginLeft: 8 }}>Wdh</span>
              <span style={{ width: 50, marginLeft: 8 }}>RPE</span>
            </div>
            {g.sets.map(s => (
              <SetRow
                key={s.id}
                set={s}
                onUpdate={aenderung => satzAendern(s.id, aenderung)}
                onDelete={() => deleteSet(s.id)}
                onToggleCompleted={isActive ? () => satzAbhaken(s) : undefined}
                zielReps={zielRepsText(g.exerciseId)}
                readonly={!isActive}
              />
            ))}
          </div>
        );
      })}

      {isActive && (
        <button
          className="btn-secondary"
          onClick={() => setShowPicker(true)}
          style={{ width: '100%', marginTop: 8 }}
        >
          + Übung hinzufügen
        </button>
      )}

      {showPicker && (
        <ExercisePicker
          onSelect={onExerciseSelected}
          onClose={() => setShowPicker(false)}
        />
      )}

      {restTimer && (
        <RestTimer
          seconds={restTimer.seconds}
          onComplete={() => setRestTimer(null)}
          onDismiss={() => setRestTimer(null)}
        />
      )}
    </div>
  );
}

function PlanDaySelector({ planId, onSelect }: { planId: number; onSelect: (dayId: number) => void }) {
  const [plan, setPlan] = useState<Plan | null>(null);

  useEffect(() => {
    api.get<Plan>(`/plans/${planId}`).then(setPlan);
  }, [planId]);

  if (!plan) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {plan.days.map(d => (
        <button
          key={d.id}
          className="btn-secondary"
          onClick={() => onSelect(d.id)}
          style={{ textAlign: 'left', padding: '12px 16px' }}
        >
          <strong>{d.name}</strong>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {d.exercises.length} Übungen
          </div>
        </button>
      ))}
    </div>
  );
}
