import { useState } from 'react';

interface ReadinessData {
  fatigue_level: number | null;
  sleep_quality: number | null;
  motivation: number | null;
  pre_notes: string;
}

interface Props {
  onStart: (data: ReadinessData) => void;
  onSkip: () => void;
  loading?: boolean;
}

const FATIGUE_OPTIONS = [
  { value: 1, emoji: '\u{1F4AA}', label: 'Frisch' },
  { value: 2, emoji: '\u{1F60A}', label: 'Gut' },
  { value: 3, emoji: '\u{1F610}', label: 'Normal' },
  { value: 4, emoji: '\u{1F634}', label: 'Muede' },
  { value: 5, emoji: '\u{1F635}', label: 'Erschoepft' },
];

const SLEEP_OPTIONS = [
  { value: 1, emoji: '\u{1F62B}', label: 'Schlecht' },
  { value: 2, emoji: '\u{1F615}', label: 'Maessig' },
  { value: 3, emoji: '\u{1F610}', label: 'OK' },
  { value: 4, emoji: '\u{1F60C}', label: 'Gut' },
  { value: 5, emoji: '\u{1F31F}', label: 'Sehr gut' },
];

const MOTIVATION_OPTIONS = [
  { value: 1, emoji: '\u{1F612}', label: 'Niedrig' },
  { value: 2, emoji: '\u{1F614}', label: 'Gering' },
  { value: 3, emoji: '\u{1F610}', label: 'Mittel' },
  { value: 4, emoji: '\u{1F642}', label: 'Hoch' },
  { value: 5, emoji: '\u{1F525}', label: 'Max' },
];

function ScaleSelector({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: number; emoji: string; label: string }[];
  value: number | null;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 8 }}>{label}</div>
      <div style={{ display: 'flex', gap: 6, justifyContent: 'space-between' }}>
        {options.map(opt => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              padding: '10px 4px',
              borderRadius: 'var(--radius)',
              background: value === opt.value ? 'var(--primary)' : 'var(--bg-input)',
              border: value === opt.value ? '2px solid var(--primary)' : '2px solid transparent',
              color: value === opt.value ? 'white' : 'var(--text)',
              transition: 'all 0.15s ease',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '1.3rem' }}>{opt.emoji}</span>
            <span style={{ fontSize: '0.65rem', fontWeight: value === opt.value ? 600 : 400 }}>
              {opt.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ReadinessCheck({ onStart, onSkip, loading }: Props) {
  const [fatigue, setFatigue] = useState<number | null>(null);
  const [sleep, setSleep] = useState<number | null>(null);
  const [motivation, setMotivation] = useState<number | null>(null);
  const [preNotes, setPreNotes] = useState('');

  const hasAnySelection = fatigue !== null || sleep !== null || motivation !== null;

  function handleStart() {
    onStart({
      fatigue_level: fatigue,
      sleep_quality: sleep,
      motivation: motivation,
      pre_notes: preNotes,
    });
  }

  return (
    <div className="card-hero fade-in" style={{ marginBottom: 16 }}>
      <h2 style={{ fontSize: '1.1rem', marginBottom: 4, color: 'var(--text)' }}>
        Bereitschafts-Check
      </h2>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
        Wie fuehlt sich dein Koerper heute an?
      </div>

      <ScaleSelector
        label="Erschoepfung"
        options={FATIGUE_OPTIONS}
        value={fatigue}
        onChange={setFatigue}
      />

      <ScaleSelector
        label="Schlafqualitaet"
        options={SLEEP_OPTIONS}
        value={sleep}
        onChange={setSleep}
      />

      <ScaleSelector
        label="Motivation"
        options={MOTIVATION_OPTIONS}
        value={motivation}
        onChange={setMotivation}
      />

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 4 }}>
          Notizen (optional)
        </div>
        <textarea
          value={preNotes}
          onChange={e => setPreNotes(e.target.value)}
          placeholder="z.B. Schulter zwickt, Koffein genommen..."
          maxLength={500}
          rows={2}
          style={{
            width: '100%',
            resize: 'vertical',
            fontSize: '0.85rem',
          }}
        />
      </div>

      <button
        className="btn-primary"
        style={{ width: '100%', padding: '12px 16px', fontSize: '1rem', fontWeight: 600, marginBottom: 8 }}
        onClick={handleStart}
        disabled={loading}
      >
        {loading ? 'Starte...' : 'Training starten'}
      </button>

      {!hasAnySelection && (
        <button
          className="btn-secondary"
          style={{ width: '100%', fontSize: '0.85rem' }}
          onClick={onSkip}
          disabled={loading}
        >
          Ohne Check starten
        </button>
      )}
    </div>
  );
}
