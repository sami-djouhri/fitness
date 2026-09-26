import { useEffect, useState } from 'react';
import type { Exercise } from '../types';
import { api } from '../api';

interface Props {
  onSelect: (exercise: Exercise) => void;
  onClose: () => void;
}

export default function ExercisePicker({ onSelect, onClose }: Props) {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    api.get<Exercise[]>(`/exercises?${params}`).then(setExercises);
  }, [search, category]);

  const categories = ['', 'Brust', 'Rücken', 'Schultern', 'Arme', 'Beine', 'Core', 'Cardio'];

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
      zIndex: 200, display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: 16, background: 'var(--bg)', flexShrink: 0 }}>
        <div className="flex-between mb-8">
          <h2 style={{ margin: 0 }}>Übung wählen</h2>
          <button className="btn-secondary btn-sm" onClick={onClose}>&times;</button>
        </div>
        <input
          placeholder="Suchen..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          autoFocus
        />
        <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
          {categories.map(c => (
            <button
              key={c}
              className={c === category ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
              onClick={() => setCategory(c)}
            >
              {c || 'Alle'}
            </button>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {exercises.map(ex => (
          <div
            key={ex.id}
            className="card"
            style={{ cursor: 'pointer' }}
            onClick={() => onSelect(ex)}
          >
            <div className="flex-between">
              <strong>{ex.name}</strong>
              <span className="chip">{ex.category}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
              {ex.equipment} {ex.is_compound ? '• Compound' : ''}
            </div>
          </div>
        ))}
        {exercises.length === 0 && <div className="empty">Keine Übungen gefunden</div>}
      </div>
    </div>
  );
}
