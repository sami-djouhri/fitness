import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Exercise, RecommendationsResponse, ExerciseRecommendation } from '../types';

const CATEGORIES = ['Brust', 'Rücken', 'Schultern', 'Arme', 'Beine', 'Core', 'Cardio', 'Dehnung'];
const EQUIPMENT = ['Langhantel', 'Kurzhantel', 'Kabelzug', 'Maschine', 'Körpergewicht', 'Band', 'Kettlebell'];

export default function ExercisesPage() {
  const navigate = useNavigate();
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [recs, setRecs] = useState<ExerciseRecommendation[]>([]);

  useEffect(() => {
    api.get<RecommendationsResponse>('/progress/recommendations')
      .then(r => setRecs(r.recommendations))
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [search, category]);

  async function load() {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    const data = await api.get<Exercise[]>(`/exercises?${params}`);
    setExercises(data);
  }

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api.post('/exercises', {
      name: fd.get('name'),
      category: fd.get('category'),
      equipment: fd.get('equipment'),
      is_compound: fd.get('is_compound') === 'on',
      primary_muscles: (fd.get('muscles') as string).split(',').map(s => s.trim()).filter(Boolean),
    });
    setShowForm(false);
    load();
  }

  // Build recommended exercise ID set
  const recIds = new Set(recs.map(r => r.exercise_id));
  const recMap = new Map(recs.map(r => [r.exercise_id, r]));

  // Sort: recommended first, then active (is_selected), then deactivated
  const sortedExercises = [...exercises].sort((a, b) => {
    const aRec = recIds.has(a.id) ? 0 : 1;
    const bRec = recIds.has(b.id) ? 0 : 1;
    if (aRec !== bRec) return aRec - bRec;
    const aActive = a.is_selected !== false ? 0 : 1;
    const bActive = b.is_selected !== false ? 0 : 1;
    return aActive - bActive;
  });

  return (
    <div className="page fade-in">
      <div className="flex-between mb-16">
        <h1>Übungen</h1>
        <button className="btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Abbrechen' : '+ Neu'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-16">
          <div className="form-group">
            <label>Name</label>
            <input name="name" required />
          </div>
          <div className="row">
            <div className="form-group">
              <label>Kategorie</label>
              <select name="category" required>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Equipment</label>
              <select name="equipment" required>
                {EQUIPMENT.map(e => <option key={e} value={e}>{e}</option>)}
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Muskeln (kommagetrennt)</label>
            <input name="muscles" placeholder="z.B. Brust, Trizeps" />
          </div>
          <div className="form-group">
            <label>
              <input type="checkbox" name="is_compound" style={{ width: 'auto', marginRight: 8 }} />
              Compound-Übung
            </label>
          </div>
          <button type="submit" className="btn-primary" style={{ width: '100%' }}>Erstellen</button>
        </form>
      )}

      <input
        placeholder="Suchen..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="mb-8"
      />

      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
        <button
          className={!category ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
          onClick={() => setCategory('')}
        >
          Alle
        </button>
        {CATEGORIES.map(c => (
          <button
            key={c}
            className={c === category ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {sortedExercises.map(ex => {
        const isRecommended = recIds.has(ex.id);
        const rec = recMap.get(ex.id);
        const isDeactivated = ex.is_selected === false;

        return (
          <div
            key={ex.id}
            className={isRecommended ? 'card-hero' : 'card'}
            onClick={() => navigate(`/exercises/${ex.id}`)}
            style={{
              cursor: 'pointer',
              opacity: isDeactivated ? 0.5 : 1,
              transition: 'transform var(--transition-fast)',
            }}
          >
            <div className="flex-between">
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong>{ex.name}</strong>
                {isRecommended && rec && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--primary)', marginTop: 2 }}>
                    {rec.reason}
                  </div>
                )}
                {/* Muscle tags */}
                {ex.primary_muscles.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                    {ex.primary_muscles.map(m => (
                      <span key={m} className="chip" style={{ fontSize: '0.7rem' }}>{m}</span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexShrink: 0 }}>
                <span className="chip">{ex.category}</span>
                {ex.is_compound && <span className="chip-compound">Compound</span>}
              </div>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
              {ex.equipment}
            </div>
          </div>
        );
      })}
      {exercises.length === 0 && <div className="empty">Keine Übungen gefunden</div>}
    </div>
  );
}
