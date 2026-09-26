import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type {
  MuscleGroupFreshness,
  ExerciseRecommendation,
  OverloadSuggestion,
  LastWeightEntry,
} from '../types';

interface Props {
  recommendations: ExerciseRecommendation[];
  freshness: MuscleGroupFreshness[];
  onStartWorkout?: (workoutId: number) => void;
}

export default function TodayTraining({ recommendations, freshness }: Props) {
  const navigate = useNavigate();
  const [suggestions, setSuggestions] = useState<Record<number, OverloadSuggestion>>({});
  const [lastWeights, setLastWeights] = useState<Record<number, LastWeightEntry>>({});

  // Find the muscle region with the greatest training need
  const targetRegion = freshness
    .filter(r => r.exercises_available > 0)
    .sort((a, b) => {
      // Prioritize: never trained (null) > most days since trained
      const aDays = a.days_since_trained ?? 999;
      const bDays = b.days_since_trained ?? 999;
      return bDays - aDays;
    })[0] || null;

  // Top 3 recommendations (matching target region preferred, then by priority score)
  const topExercises = recommendations.slice(0, 3);

  useEffect(() => {
    if (topExercises.length === 0) return;
    const ids = topExercises.map(e => e.exercise_id);

    // Load last weights
    api.get<LastWeightEntry[]>(`/workouts/last-weights?exercise_ids=${ids.join(',')}`)
      .then(entries => {
        const map: Record<number, LastWeightEntry> = {};
        for (const e of entries) map[e.exercise_id] = e;
        setLastWeights(map);
      })
      .catch(() => {});

    // Load overload suggestions
    for (const ex of topExercises) {
      api.get<OverloadSuggestion>(`/workouts/suggestions?exercise_id=${ex.exercise_id}`)
        .then(s => setSuggestions(prev => ({ ...prev, [ex.exercise_id]: s })))
        .catch(() => {});
    }
  }, [recommendations]);

  if (topExercises.length === 0 || !targetRegion) return null;

  const daysText = targetRegion.days_since_trained === null
    ? 'Noch nie trainiert'
    : targetRegion.days_since_trained === 0
      ? 'Heute trainiert'
      : targetRegion.days_since_trained === 1
        ? 'Gestern trainiert'
        : `Vor ${targetRegion.days_since_trained} Tagen trainiert`;

  const freshnessColor = targetRegion.color;

  function handleStart() {
    // Die drei angezeigten Uebungen wandern mit in die Session. Vorher startete
    // dieser Knopf ein leeres Training, in dem keine davon stand: der Nutzer
    // sah "Bankdruecken 60kg x 8", drueckte "Training starten" und stand vor
    // einem leeren Bildschirm.
    navigate('/workout', {
      state: {
        pendingName: `${targetRegion!.label} Training`,
        pendingExerciseIds: topExercises.map(e => e.exercise_id),
      },
    });
  }

  return (
    <div className="card-hero today-training">
      {/* Status line */}
      <div className="status-line">
        <span className="status-dot" style={{ background: freshnessColor }} />
        <span><strong>{targetRegion.label}</strong>: {daysText}</span>
      </div>

      {/* Top 3 exercises */}
      {topExercises.map(ex => {
        const lw = lastWeights[ex.exercise_id];
        const sug = suggestions[ex.exercise_id];
        return (
          <div key={ex.exercise_id} className="today-exercise">
            <div className="ex-info">
              <div className="ex-name">{ex.exercise_name}</div>
              <div className="ex-meta">
                {ex.reason}
                {ex.is_compound && <> &middot; <span style={{ color: 'var(--success)' }}>Compound</span></>}
              </div>
            </div>
            <div className="ex-weight">
              {sug?.suggested_weight_kg
                ? <><strong style={{ color: 'var(--primary)' }}>{sug.suggested_weight_kg}kg</strong> &times; {sug.suggested_reps}</>
                : lw?.weight_kg
                  ? <>{lw.weight_kg}kg &times; {lw.reps}</>
                  : '–'
              }
            </div>
          </div>
        );
      })}

      {/* Start button */}
      <button
        className="btn-primary"
        style={{ width: '100%', padding: '12px 16px', fontSize: '1rem', fontWeight: 600 }}
        onClick={handleStart}
      >
        Training starten
      </button>
    </div>
  );
}
