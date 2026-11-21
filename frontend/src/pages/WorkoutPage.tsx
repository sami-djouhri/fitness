import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api, NetzFehler } from '../api';
import type { Workout, WorkoutSet, Exercise, PlanListItem, Plan, OverloadSuggestion, LastWeightEntry, TrainingJetzt, PlanTarget, StartUebung } from '../types';
import { startzustand, ziel } from '../trainingjetzt';
import { aufIdAufloesung } from '../warteschlange';
import { jetztAusVorrat, jetztMerken, lokalEntfernen, lokalLaden, lokalSpeichern, namenAus, offlineStarten } from '../offlinetraining';
import ExercisePicker from '../components/ExercisePicker';
import SetRow from '../components/SetRow';
import RestTimer from '../components/RestTimer';
import BereitschaftZeile from '../components/BereitschaftZeile';

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
  const [jetzt, setJetzt] = useState<TrainingJetzt | null>(null);
  const [pendingWorkout, setPendingWorkout] = useState<{ plan_day_id?: number; name?: string; exercise_ids?: number[]; uebungen?: StartUebung[]; namen?: Record<number, string>; pausen?: Record<number, number> } | null>(null);
  /** Gesetzt, wenn die Auskunft aus dem Vorrat stammt (offline). */
  const [vorratAm, setVorratAm] = useState<string | null>(null);
  const [startFehler, setStartFehler] = useState<string | null>(null);
  const [bereitschaftZu, setBereitschaftZu] = useState(false);
  const startAngestossen = useRef(false);
  const [namensAbfrage, setNamensAbfrage] = useState<string | null>(null);
  const [startingWorkout, setStartingWorkout] = useState(false);
  const [ladeFehler, setLadeFehler] = useState<string | null>(null);
  /** Gerade geloeschter Satz, solange „Rückgängig“ noch geht. */
  const [geloescht, setGeloescht] = useState<{ satz: WorkoutSet; stelle: number } | null>(null);
  const geloeschtRef = useRef<{ satz: WorkoutSet; stelle: number } | null>(null);
  const loeschWecker = useRef<ReturnType<typeof setTimeout>>();
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const isNew = !id;

  // Vorgemerkte Session aus der Navigation uebernehmen (Startseite, Planseite).
  useEffect(() => {
    const state = location.state as {
      pendingName?: string;
      pendingPlanDayId?: number;
      pendingExerciseIds?: number[];
      pendingUebungen?: StartUebung[];
      pendingNamen?: Record<number, string>;
      pendingPausen?: Record<number, number>;
    } | null;
    if (state && !id) {
      if (state.pendingName || state.pendingPlanDayId || state.pendingExerciseIds
          || state.pendingUebungen) {
        setPendingWorkout({
          name: state.pendingName,
          plan_day_id: state.pendingPlanDayId,
          exercise_ids: state.pendingExerciseIds,
          uebungen: state.pendingUebungen,
          namen: state.pendingNamen,
          pausen: state.pendingPausen,
        });
        // Clear the navigation state so it doesn't re-trigger
        window.history.replaceState({}, '');
      }
    }
  }, [location.state, id]);

  useEffect(() => {
    if (id) {
      // Ohne Abfangen blieb die Seite bei einem Fehler für immer auf
      // „Laden...“ stehen, auch ohne Netz im Gym.
      setLadeFehler(null);
      loadWorkout(parseInt(id)).catch((e) => setLadeFehler(String(e instanceof Error ? e.message : e)));
    } else {
      api.get<PlanListItem[]>('/plans').then(setPlans).catch(() => {});
      // Dieselbe Auskunft wie auf der Startseite, seit dem 2026-10-24.
      // Vorher suchte sich diese Seite die am laengsten unberuehrte Region aus
      // ``/progress/muscle-freshness`` und bot "Rücken Training" an. Das war
      // die vierte Logik fuer dieselbe Frage und zugleich die duennste: sie
      // kannte nur eine Region, keine Uebungen, keine Zeit und keine
      // Ausruestung, und der Startknopf legte eine Sitzung mit Namen und
      // **ohne eine einzige Uebung** an.
      api.get<TrainingJetzt>('/training/jetzt')
        .then((j) => { setJetzt(j); setVorratAm(null); jetztMerken(j); })
        .catch((e) => {
          // Offline: der zuletzt gemerkte Vorschlag, mit seinem Stand.
          const v = e instanceof NetzFehler ? jetztAusVorrat() : null;
          if (v) { setJetzt(v.jetzt); setVorratAm(v.am); }
        });
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
    setWorkout(prev => {
      if (!prev) return prev;
      if (prev.id === ersatzId) {
        // Das offline begonnene Training ist beim Dienst angekommen: ab jetzt
        // unter seiner echten Kennung, die lokale Kopie hat ausgedient.
        lokalEntfernen(ersatzId);
        navigate(`/workout/${echteId}`, { replace: true });
        return { ...prev, id: echteId };
      }
      return { ...prev, sets: prev.sets.map(s => s.id === ersatzId ? { ...s, id: echteId } : s) };
    });
  }), []);

  // Offline begonnen: jede Aenderung in die lokale Kopie, damit ein Neuladen
  // im Funkloch das Training nicht verliert.
  useEffect(() => {
    if (workout && workout.id < 0) lokalSpeichern(workout);
  }, [workout]);

  async function loadWorkout(wid: number) {
    if (wid < 0) {
      const lokal = lokalLaden(wid);
      if (!lokal) throw new Error('Dieses offline begonnene Training liegt nicht auf diesem Gerät');
      setWorkout(lokal);
      return;
    }
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

  /**
   * Startet genau das, was darüber steht, samt Sätzen und Gewichten.
   *
   * Der Vorgänger übergab nur einen Namen. Die Sitzung war danach leer, und
   * jede Übung musste von Hand aus dem Katalog gesucht werden.
   */
  function startRecWorkout() {
    if (!jetzt || jetzt.uebungen.length === 0) return;
    const zustand = startzustand(jetzt);
    setPendingWorkout({
      name: zustand.pendingName,
      plan_day_id: zustand.pendingPlanDayId,
      uebungen: zustand.pendingUebungen,
      namen: zustand.pendingNamen,
      pausen: zustand.pendingPausen,
    });
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

  /**
   * Legt die Einheit an. Ohne Netz geht der Start in die Warteschlange
   * (``offlinetraining.ts``) und die Seite zeigt die lokale Kopie; bis
   * 2026-11-21 blieb sie hier mit einem Fehler stehen.
   */
  async function anlegen(bereitschaft: Record<string, unknown>) {
    if (!pendingWorkout) return;
    setStartingWorkout(true);
    setStartFehler(null);
    const rumpf = {
      plan_day_id: pendingWorkout.plan_day_id ?? null,
      name: pendingWorkout.name,
      exercise_ids: pendingWorkout.exercise_ids ?? null,
      uebungen: pendingWorkout.uebungen ?? null,
      ...bereitschaft,
    };
    try {
      const w = await api.post<Workout>('/workouts', rumpf);
      navigate(`/workout/${w.id}`, { replace: true });
    } catch (fehler) {
      if (!(fehler instanceof NetzFehler)) {
        setStartFehler(fehler instanceof Error ? fehler.message : String(fehler));
        return;
      }
      try {
        const lokal = offlineStarten({
          name: pendingWorkout.name,
          plan_day_id: pendingWorkout.plan_day_id,
          uebungen: pendingWorkout.uebungen ?? [],
          namen: pendingWorkout.namen ?? namenAus(jetzt).namen,
          pausen: pendingWorkout.pausen ?? namenAus(jetzt).pausen,
          bereitschaft,
        });
        navigate(`/workout/${lokal.id}`, { replace: true });
      } catch (offlineFehler) {
        setStartFehler(offlineFehler instanceof Error ? offlineFehler.message : String(offlineFehler));
      }
    } finally {
      setStartingWorkout(false);
    }
  }

  /**
   * Ein Tipp auf „Starten“ legt die Einheit an (seit 2026-11-21). Vorher
   * stand der Bereitschafts-Check als eigener Bildschirm dazwischen; er ist
   * jetzt eine freiwillige Zeile im Training (``BereitschaftZeile``).
   */
  useEffect(() => {
    if (!isNew || !pendingWorkout || startAngestossen.current) return;
    startAngestossen.current = true;
    meldungErlauben();
    void anlegen({});
  }, [pendingWorkout, isNew]);

  function bereitschaftSetzen(feld: 'fatigue_level' | 'sleep_quality' | 'motivation', wert: number) {
    if (!workout) return;
    setWorkout({ ...workout, [feld]: wert });
    void api.putRobust(`/workouts/${workout.id}`, { [feld]: wert });
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

  /**
   * Loeschen mit Rueckgaengig (Entscheid 2026-11-08): der Satz
   * verschwindet sofort, an den Dienst geht das Loeschen erst nach 5 s, beim
   * naechsten Loeschen, beim Beenden oder beim Verlassen der Seite.
   *
   * Bewusst aufgeschoben statt geloescht und wieder angelegt: ein neu
   * angelegter Satz bekaeme eine neue Kennung und ein neues `completed_at`,
   * und `_check_prs` liefe ein zweites Mal, ein Rekord truege dann die Zeit
   * des Rueckgaengig. Aufgeschoben erfaehrt der Dienst von einem
   * zurueckgenommenen Loeschen nie etwas.
   */
  function loeschenAbschicken() {
    clearTimeout(loeschWecker.current);
    const offen = geloeschtRef.current;
    geloeschtRef.current = null;
    setGeloescht(null);
    if (offen) return api.delRobust(`/workouts/sets/${offen.satz.id}`);
    return Promise.resolve();
  }

  function deleteSet(setId: number) {
    if (!workout) return;
    void loeschenAbschicken();
    const stelle = workout.sets.findIndex(s => s.id === setId);
    if (stelle < 0) return;
    const eintrag = { satz: workout.sets[stelle], stelle };
    geloeschtRef.current = eintrag;
    setGeloescht(eintrag);
    setWorkout(prev => prev ? { ...prev, sets: prev.sets.filter(s => s.id !== setId) } : prev);
    loeschWecker.current = setTimeout(() => { void loeschenAbschicken(); }, 5000);
  }

  function loeschenZuruecknehmen() {
    clearTimeout(loeschWecker.current);
    const offen = geloeschtRef.current;
    geloeschtRef.current = null;
    setGeloescht(null);
    if (!offen) return;
    setWorkout(prev => {
      if (!prev) return prev;
      const sets = [...prev.sets];
      sets.splice(Math.min(offen.stelle, sets.length), 0, offen.satz);
      return { ...prev, sets };
    });
  }

  // Seite verlassen (anderer Reiter, App schliessen): ein offenes Loeschen
  // geht sofort raus, sonst stuende der Satz beim naechsten Laden wieder da.
  useEffect(() => {
    const beimVerlassen = () => { void loeschenAbschicken(); };
    window.addEventListener('pagehide', beimVerlassen);
    return () => {
      window.removeEventListener('pagehide', beimVerlassen);
      beimVerlassen();
    };
  }, []);

  async function finishWorkout() {
    if (!workout) return;
    await loeschenAbschicken();
    // Nachtragbar: wer im Funkloch beendet, verliert sonst das Ende.
    await api.postNachtragbar(`/workouts/${workout.id}/finish`);
    if (workout.id < 0) setWorkout({ ...workout, finished_at: new Date().toISOString() });
    setShowRating(true);
  }

  async function submitRating(rating: number) {
    if (!workout) return;
    await api.putRobust(`/workouts/${workout.id}`, { rating });
    navigate('/');
  }

  async function skipRating() {
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
              aria-label={`${star} von 5 Sternen`}
              aria-pressed={star === ratingValue}
              onClick={() => setRatingValue(star)}
            >
              
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

  // Start laeuft (ein Tipp, kein Zwischenbildschirm mehr)
  if (isNew && !workout && pendingWorkout) {
    return (
      <div className="page fade-in">
        {startFehler ? (
          <div className="leer">
            Das Training ließ sich nicht starten ({startFehler}).{' '}
            <button className="btn-secondary btn-sm" onClick={() => {
              setStartFehler(null);
              void anlegen({});
            }}>Erneut versuchen</button>{' '}
            <button className="btn-secondary btn-sm" onClick={() => {
              setStartFehler(null);
              startAngestossen.current = false;
              setPendingWorkout(null);
            }}>Zurück</button>
          </div>
        ) : (
          <div className="leer">Training startet …</div>
        )}
      </div>
    );
  }

  // Start screen
  if (isNew && !workout) {
    const activePlan = plans.find(p => p.is_active);
    return (
      <div className="page fade-in">
        <h1>Workout starten</h1>

        {/* Dieselbe Antwort wie auf der Startseite, aus demselben Dienst. */}
        {jetzt && jetzt.uebungen.length > 0 && (
          <div className="card-hero" style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              {jetzt.quelle === 'plan' ? 'Nach Plan dran' : 'Vorschlag für heute'}
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>{jetzt.titel}</div>
            {vorratAm && (
              <div className="klein gedaempft" style={{ marginBottom: 8 }}>
                Ohne Netz: Vorschlag vom {new Date(vorratAm).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })}.
                Das Training wird nachgetragen, sobald wieder Netz da ist.
              </div>
            )}
            <div className="heute-uebungen">
              {jetzt.uebungen.map((u) => (
                <div key={u.exercise_id} className="heute-uebung">
                  <span>{u.name}</span>
                  <span className="ziel">{ziel(u)}</span>
                </div>
              ))}
            </div>
            {jetzt.uebungen.some((u) => u.gewicht_quelle === 'geschaetzt') && (
              <div className="klein gedaempft" style={{ marginBottom: 10 }}>
                ~ ist geschätzt, aus Körpergewicht und Erfahrung.
              </div>
            )}
            <button className="btn-primary" style={{ width: '100%' }} onClick={startRecWorkout}>
              Starten ({jetzt.geplante_minuten} min)
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

  if (!workout && ladeFehler) {
    return (
      <div className="page fade-in">
        <div className="leer">
          Die Einheit ließ sich nicht laden ({ladeFehler}).{' '}
          <button className="btn-secondary btn-sm" onClick={() => {
            setLadeFehler(null);
            loadWorkout(parseInt(id!)).catch((e) => setLadeFehler(String(e instanceof Error ? e.message : e)));
          }}>Erneut versuchen</button>
        </div>
      </div>
    );
  }
  if (!workout) return <div className="page fade-in"><div className="leer">Lädt …</div></div>;

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
              {workout.rating && ` · ${''.repeat(workout.rating)}${'☆'.repeat(5 - workout.rating)}`}
            </div>
          )}
        </div>
        {isActive && (
          <button className="btn-primary" onClick={finishWorkout}>Beenden</button>
        )}
      </div>

      {isActive && !bereitschaftZu && !(workout.fatigue_level && workout.sleep_quality && workout.motivation) && (
        <BereitschaftZeile
          werte={{ fatigue_level: workout.fatigue_level, sleep_quality: workout.sleep_quality, motivation: workout.motivation }}
          onWert={bereitschaftSetzen}
          onSchliessen={() => setBereitschaftZu(true)}
        />
      )}

      {/* Pre-workout readiness data */}
      {(!isActive || bereitschaftZu || (workout.fatigue_level && workout.sleep_quality && workout.motivation))
        && (workout.fatigue_level || workout.sleep_quality || workout.motivation || workout.pre_notes) && (
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
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {['Frisch', 'Gut', 'Normal', 'Müde', 'Erschöpft'][workout.fatigue_level - 1]}
                </div>
              </div>
            )}
            {workout.sleep_quality && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.1rem' }}>
                  {['\u{1F62B}', '\u{1F615}', '\u{1F610}', '\u{1F60C}', '\u{1F31F}'][workout.sleep_quality - 1]}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Schlaf: {['Schlecht', 'Mäßig', 'OK', 'Gut', 'Sehr gut'][workout.sleep_quality - 1]}
                </div>
              </div>
            )}
            {workout.motivation && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.1rem' }}>
                  {['\u{1F612}', '\u{1F614}', '\u{1F610}', '\u{1F642}', '\u{1F525}'][workout.motivation - 1]}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
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
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {vorgabeText(g.exerciseId)}
                    {' \u00b7 '}
                    {g.sets.filter(s => s.is_completed).length}/{g.sets.length} erledigt
                  </div>
                )}
                {isInSuperset && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--warning)', fontWeight: 600 }}>
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
                      style={{ fontSize: '0.9rem', padding: '0 2px', minHeight: 44, width: 44 }}
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
                    style={{ fontSize: '1.1rem', padding: '0 2px', minHeight: 44, width: 44 }}
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

      {geloescht && (
        <div className="rueckgaengig-leiste" role="status">
          <span>Satz gelöscht</span>
          <button type="button" onClick={loeschenZuruecknehmen}>Rückgängig</button>
        </div>
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
