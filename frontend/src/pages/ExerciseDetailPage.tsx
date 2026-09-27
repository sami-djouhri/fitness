import { lazy, Suspense, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type {
  Exercise,
  ExerciseHistorySession,
  ExerciseProgressPoint,
  PersonalRecord,
  StrengthLevel,
  Progressionsvorschlag,
} from '../types';
import ProgressChart from '../components/ProgressChart';

/** Wie auf der Körperseite nachgeladen: three.js gehört nicht ins Hauptbündel. */
const Koerpermodell = lazy(() => import('../components/Koerpermodell'));

export default function ExerciseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [history, setHistory] = useState<ExerciseHistorySession[]>([]);
  const [progress, setProgress] = useState<ExerciseProgressPoint[]>([]);
  const [prs, setPrs] = useState<PersonalRecord[]>([]);
  const [strengthLevel, setStrengthLevel] = useState<StrengthLevel | null>(null);
  const [suggestion, setSuggestion] = useState<Progressionsvorschlag | null>(null);
  const [zeigtBewegung, setZeigtBewegung] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAllHistory, setShowAllHistory] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');

  const exerciseId = id ? parseInt(id) : null;

  useEffect(() => {
    if (!exerciseId) {
      setError('Übungs-ID nicht gefunden');
      setLoading(false);
      return;
    }
    loadData();
  }, [exerciseId]);

  async function loadData() {
    try {
      setLoading(true);
      setError('');

      const [ex, hist, prog, prRecords, strength, sug] = await Promise.all([
        api.get<Exercise>(`/exercises/${exerciseId}`),
        api.get<ExerciseHistorySession[]>(`/progress/exercise/${exerciseId}/history?limit=10`),
        api.get<ExerciseProgressPoint[]>(`/progress/exercise/${exerciseId}?days=365`),
        api.get<PersonalRecord[]>(`/progress/prs?exercise_id=${exerciseId}`),
        api.get<StrengthLevel>(`/progress/strength-level?exercise_id=${exerciseId}`),
        // Seit 2026-09 der Progressionsdienst statt `/workouts/suggestions`:
        // der kannte zwei Faelle und verglich jede Uebung mit einer fest
        // eingebauten Zwoelf, unabhaengig von ihrem Zielbereich.
        api.get<Progressionsvorschlag>(`/exercises/${exerciseId}/progression`).catch(() => null),
      ]);

      setExercise(ex);
      setEditName(ex.name);
      setHistory(hist);
      setProgress(prog);
      setPrs(prRecords);
      setStrengthLevel(strength);
      setSuggestion(sug);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm('Übung wirklich löschen?')) return;
    try {
      await api.del(`/exercises/${exerciseId}`);
      navigate('/exercises');
    } catch (err) {
      // Der Server lehnt ab, wenn die Uebung in einem Plan oder Workout
      // haengt oder zum gemeinsamen Katalog gehoert. Diese Begruendung
      // gehoert auf den Bildschirm, nicht in die Konsole.
      setError(err instanceof Error ? err.message : 'Löschen nicht möglich');
    }
  }

  if (loading) {
    return (
      <div className="page fade-in">
        <div className="skeleton" style={{ height: 20, width: 80, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 120, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 80, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  if (error || !exercise) {
    return (
      <div className="page fade-in">
        <button className="btn-secondary btn-sm" onClick={() => navigate('/exercises')}>
          ← Zurück
        </button>
        <div style={{ marginTop: 12, color: 'var(--text-muted)' }}>
          {error || 'Übung nicht gefunden'}
        </div>
      </div>
    );
  }

  const prTypeLabels: Record<string, string> = {
    '1rm': 'Geschätztes 1RM',
    'max_weight': 'Max. Gewicht',
    'max_reps': 'Max. Wiederholungen',
    'max_volume': 'Max. Volumen',
  };

  const getLevelProgress = () => {
    if (!strengthLevel) return 0;
    const levels = Object.entries(strengthLevel.levels).sort(
      ([, a], [, b]) => a - b
    );
    const currentIdx = levels.findIndex(([name]) => name === strengthLevel.level);
    return currentIdx >= 0 ? ((currentIdx + 1) / levels.length) * 100 : 0;
  };

  const visibleHistory = showAllHistory ? history : history.slice(0, 3);

  return (
    <div className="page fade-in">
      {/* Back Button */}
      <button className="btn-secondary btn-sm" onClick={() => navigate('/exercises')}>
        ← Zurück
      </button>

      {/* 1. Identity Hero Card */}
      <div className="card-hero" style={{ marginTop: 12 }}>
        <h1 style={{ marginBottom: 8 }}>{exercise.name}</h1>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 }}>
          <span className="chip">{exercise.category}</span>
          {exercise.is_compound && <span className="chip-compound">Compound</span>}
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {exercise.equipment}
          </span>
        </div>
        {exercise.primary_muscles.length > 0 && (
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Primär: </span>
            {exercise.primary_muscles.map((m, i) => (
              <span key={i} className="chip" style={{ marginRight: 4 }}>{m}</span>
            ))}
          </div>
        )}
        {exercise.secondary_muscles.length > 0 && (
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Sekundär: </span>
            {exercise.secondary_muscles.map((m, i) => (
              <span key={i} className="chip" style={{ marginRight: 4 }}>{m}</span>
            ))}
          </div>
        )}
      </div>

      {/* 1b. Die Bewegung, am Modell vorgeführt.
           ★ Animiert wird das Bewegungsmuster der Übung, nicht die Übung
           selbst: 22 Muster decken alle 167 Einträge ab. Eine eigene
           Keyframe-Spur je Übung hätte bedeutet, dass die letzten fünfzig
           nie eine bekommen. */}
      {exercise.muster && (
        <div className="karte" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="karte-kopf" style={{ padding: '12px 14px 0', marginBottom: 0 }}>
            <strong>Bewegung</strong>
            <button className="knopf-flach" onClick={() => setZeigtBewegung(!zeigtBewegung)}>
              {zeigtBewegung ? 'anhalten' : 'abspielen'}
            </button>
          </div>
          <Suspense fallback={<div className="skeleton" style={{ height: 320, margin: 12 }} />}>
            <Koerpermodell
              werte={Object.fromEntries(
                Object.entries(exercise.muskel_anteile ?? {}))}
              faerbung="abdeckung"
              hoehe={320}
              muster={zeigtBewegung ? exercise.muster : null}
              fusszeile={exercise.ausfuehrung ?? undefined}
            />
          </Suspense>
          {exercise.fehler && (
            <div style={{ padding: '0 14px 12px' }}>
              <span className="klein warnung">Häufiger Fehler: </span>
              <span className="klein gedaempft">{exercise.fehler}</span>
            </div>
          )}
        </div>
      )}

      {/* 2. Was beim nächsten Mal dran ist */}
      {suggestion && (
        <div className="overload-suggestion">
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Nächstes Training
          </div>
          <div className="overload-values">
            {suggestion.gewicht_kg != null && (
              <div className="overload-value">
                {suggestion.gewicht_kg}<span className="unit"> kg</span>
              </div>
            )}
            {suggestion.wdh != null && (
              <div className="overload-value">
                {suggestion.wdh}
                <span className="unit">{exercise.ist_zeit ? ' s' : ' Wdh'}</span>
              </div>
            )}
          </div>
          <div className="overload-reason">{suggestion.begruendung}</div>
          {suggestion.letztes_gewicht_kg != null && (
            <div className="overload-last">
              Zuletzt: {suggestion.letztes_gewicht_kg} kg x {suggestion.letzte_wdh}
            </div>
          )}
          {suggestion.aufwaermsaetze.length > 0 && (
            <div className="overload-last">
              Aufwärmen:{' '}
              {suggestion.aufwaermsaetze.map((s) => `${s.gewicht_kg} x ${s.wdh}`).join(', ')}
            </div>
          )}
          {suggestion.plateau_seit >= 3 && (
            <div className="klein warnung">
              Seit {suggestion.plateau_seit} Einheiten kein Zuwachs.
            </div>
          )}
        </div>
      )}

      {/* 3. Strength Level + Personal Records */}
      {(strengthLevel || prs.length > 0) && (
        <div className="card mb-16">
          {strengthLevel && (
            <>
              <div className="flex-between mb-8">
                <div>
                  <strong>Kraftlevel</strong>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    1RM: {strengthLevel.current_1rm ? strengthLevel.current_1rm.toFixed(1) : '–'} kg
                  </div>
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary)' }}>
                  {strengthLevel.level}
                </div>
              </div>
              <div style={{ marginBottom: prs.length > 0 ? 12 : 0 }}>
                <div style={{
                  width: '100%', height: 8,
                  backgroundColor: 'var(--bg-input)', borderRadius: 4, overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${getLevelProgress()}%`, height: '100%',
                    backgroundColor: 'var(--primary)', transition: 'width 0.3s ease',
                  }} />
                </div>
                <div style={{ marginTop: 6, fontSize: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {Object.entries(strengthLevel.levels)
                    .sort(([, a], [, b]) => a - b)
                    .map(([levelName, threshold]) => (
                      <span key={levelName} style={{
                        color: levelName === strengthLevel.level ? 'var(--primary)' : 'var(--text-muted)',
                        fontWeight: levelName === strengthLevel.level ? 700 : 400,
                      }}>
                        {levelName} ({threshold.toFixed(1)})
                      </span>
                    ))}
                </div>
              </div>
            </>
          )}

          {prs.length > 0 && (
            <>
              {strengthLevel && <div style={{ borderTop: '1px solid var(--border)', marginBottom: 12 }} />}
              <strong style={{ display: 'block', marginBottom: 8 }}>Persönliche Rekorde</strong>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {prs.map((pr) => (
                  <div key={pr.id} className="flex-between" style={{ padding: '4px 0' }}>
                    <div>
                      <span style={{ fontSize: '0.85rem' }}>{prTypeLabels[pr.pr_type] || pr.pr_type}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 8 }}>
                        {formatDate(pr.achieved_at)}
                      </span>
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--success)' }}>
                      {pr.value.toFixed(1)}{pr.pr_type === 'max_reps' ? '' : ' kg'}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* 4. 1RM Progression Chart */}
      {progress.length > 0 && (
        <div className="mb-16">
          <h2>1RM Entwicklung</h2>
          <ProgressChart
            data={progress}
            lines={[
              { key: 'estimated_1rm', color: 'var(--success)', name: 'Geschätztes 1RM (kg)' },
              { key: 'total_volume', color: 'var(--primary)', name: 'Volumen (kg)' },
            ]}
          />
        </div>
      )}

      {/* 5. Training History (3 visible, rest behind toggle) */}
      <div className="mb-16">
        <h2>Letzte Trainingseinheiten</h2>
        {history.length > 0 ? (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {visibleHistory.map((session) => (
                <div key={`${session.date}-${session.workout_id}`} className="card" style={{ marginBottom: 0 }}>
                  <div className="flex-between mb-8">
                    <div>
                      <strong style={{ fontSize: '0.9rem' }}>{session.workout_name}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatDate(session.date)}
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {session.sets.length > 0 ? (
                      session.sets.map((set, idx) => (
                        <div key={idx}>
                          Satz {set.set_number}: {set.weight_kg ? `${set.weight_kg} kg` : '–'}{' '}
                          {set.reps ? `× ${set.reps}` : ''}
                        </div>
                      ))
                    ) : (
                      <div>Keine Sätze</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {history.length > 3 && (
              <button
                className="btn-secondary btn-sm"
                onClick={() => setShowAllHistory(!showAllHistory)}
                style={{ width: '100%', marginTop: 8 }}
              >
                {showAllHistory ? 'Weniger anzeigen' : `Alle ${history.length} anzeigen`}
              </button>
            )}
          </>
        ) : (
          <div className="empty">Keine Trainingseinheiten vorhanden</div>
        )}
      </div>

      {/* 6. Aktionen: nur bei selbst angelegten Uebungen. Eintraege des
           gemeinsamen Katalogs aendert niemand, und ein Knopf, der immer in
           eine Fehlermeldung laeuft, ist schlechter als keiner. */}
      {exercise?.is_eigene ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn-secondary"
            style={{ flex: 1 }}
            onClick={() => setEditing(!editing)}
          >
            {editing ? 'Abbrechen' : 'Bearbeiten'}
          </button>
          <button
            className="btn-danger"
            style={{ flex: 0 }}
            onClick={handleDelete}
          >
            Löschen
          </button>
        </div>
      ) : (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
          Teil des gemeinsamen Übungskatalogs. In der Übungsliste abwählen
          blendet sie für dich aus.
        </div>
      )}
      {editing && (
        <div className="card" style={{ marginTop: 8 }}>
          <div className="form-group">
            <label>Name</label>
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
            />
          </div>
          <button
            className="btn-primary btn-sm"
            onClick={async () => {
              await api.put(`/exercises/${exerciseId}`, { name: editName });
              setEditing(false);
              loadData();
            }}
          >
            Speichern
          </button>
        </div>
      )}
    </div>
  );
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}
