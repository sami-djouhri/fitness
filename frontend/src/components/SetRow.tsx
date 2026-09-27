import { useState, useRef } from 'react';
import type { WorkoutSet } from '../types';
import { api } from '../api';
import Scheiben from './Scheiben';

const SET_TYPE_LABELS: Record<string, string> = {
  normal: '',
  warmup: 'W',
  dropset: 'D',
  failure: 'F',
  rest_pause: 'RP',
};

const SET_TYPE_COLORS: Record<string, string> = {
  warmup: '#facc15',
  dropset: '#f97316',
  failure: '#ef4444',
  rest_pause: '#a855f7',
};

interface Props {
  set: WorkoutSet;
  /** Uebernimmt die Aenderung sofort in die Anzeige, bevor der Server antwortet. */
  onUpdate: (aenderung: Partial<WorkoutSet>) => void;
  onDelete: () => void;
  /** Haken setzen oder loesen. Fehlt bei abgeschlossenen Sessions. */
  onToggleCompleted?: () => void;
  /** Ziel-Wiederholungen des Plans, als blasser Hinweis im leeren Feld. */
  zielReps?: string;
  readonly?: boolean;
}

export default function SetRow({ set, onUpdate, onDelete, onToggleCompleted, zielReps, readonly }: Props) {
  const [editing, setEditing] = useState(false);
  const [weight, setWeight] = useState(set.weight_kg?.toString() ?? '');
  const [reps, setReps] = useState(set.reps?.toString() ?? '');
  const [rpe, setRpe] = useState(set.rpe?.toString() ?? '');
  const [swipeX, setSwipeX] = useState(0);
  const touchRef = useRef<{ startX: number; startY: number; swiping: boolean } | null>(null);

  async function save() {
    const aenderung = {
      weight_kg: weight ? parseFloat(weight) : null,
      reps: reps ? parseInt(reps) : null,
      rpe: rpe ? parseFloat(rpe) : null,
    };
    setEditing(false);
    onUpdate(aenderung);  // zuerst sichtbar, dann uebertragen
    await api.putRobust(`/workouts/sets/${set.id}`, aenderung);
  }

  const handleTouchStart = (e: React.TouchEvent) => {
    if (readonly || editing) return;
    const t = e.touches[0];
    touchRef.current = { startX: t.clientX, startY: t.clientY, swiping: false };
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchRef.current || readonly || editing) return;
    const t = e.touches[0];
    const dx = t.clientX - touchRef.current.startX;
    const dy = t.clientY - touchRef.current.startY;

    // Only activate horizontal swipe if mostly horizontal
    if (!touchRef.current.swiping && Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      touchRef.current.swiping = true;
    }

    if (touchRef.current.swiping) {
      setSwipeX(Math.min(0, Math.max(-80, dx)));
    }
  };

  const handleTouchEnd = () => {
    if (!touchRef.current) return;
    if (swipeX < -50) {
      setSwipeX(-80); // Snap to reveal delete
    } else {
      setSwipeX(0);
    }
    touchRef.current = null;
  };

  // ★ Vorher: `SET_TYPE_LABELS[set.set_type] || set.set_type`. Fuer den
  // Normalfall ist das Kuerzel absichtlich leer, und der Oder-Ausdruck fiel
  // damit auf den Typnamen zurueck: in jeder Zeile eines normalen Satzes
  // stand "normal" statt der Satznummer. Im Code sieht die Zeile harmlos aus,
  // sichtbar wurde es erst, als ueberhaupt Saetze auf dem Bildschirm standen.
  const typeLabel = set.set_type in SET_TYPE_LABELS
    ? SET_TYPE_LABELS[set.set_type]
    : set.set_type;
  const typeColor = SET_TYPE_COLORS[set.set_type];
  const displayNum = typeLabel || set.set_number;

  if (editing) {
    return (
      <div className="row" style={{ padding: '4px 0' }}>
        <span style={{ width: 30, color: typeColor || 'var(--text-muted)', fontSize: '0.85rem', fontWeight: typeLabel ? 700 : 400 }}>
          {displayNum}
        </span>
        <input
          type="number" inputMode="decimal" placeholder="kg" value={weight}
          onChange={e => setWeight(e.target.value)}
          style={{ width: 70 }}
          autoFocus
        />
        <input
          type="number" inputMode="numeric" placeholder={zielReps || 'Wdh'} value={reps}
          onChange={e => setReps(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') void save(); }}
          style={{ width: 60 }}
        />
        <input
          type="number" placeholder="RPE" value={rpe}
          onChange={e => setRpe(e.target.value)}
          style={{ width: 60 }}
          step="0.5"
        />
        <button className="btn-primary btn-sm" onClick={save}>OK</button>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Delete button behind */}
      {!readonly && (
        <div
          style={{
            position: 'absolute', right: 0, top: 0, bottom: 0,
            width: 80, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'var(--danger)', color: '#fff', fontWeight: 700, fontSize: '0.8rem',
            cursor: 'pointer',
          }}
          onClick={() => { onDelete(); setSwipeX(0); }}
        >
          Löschen
        </div>
      )}
      <div
        className="row"
        style={{
          padding: '4px 0', fontSize: '0.9rem',
          transform: `translateX(${swipeX}px)`,
          transition: touchRef.current?.swiping ? 'none' : 'transform 0.2s ease',
          background: 'var(--bg-card)',
          position: 'relative',
          zIndex: 1,
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <span style={{ width: 30, color: typeColor || 'var(--text-muted)', fontWeight: typeLabel ? 700 : 400 }}>
          {displayNum}
        </span>
        {/* Geplante Saetze stehen blass da, bis sie abgehakt sind. Ohne diesen
            Unterschied sieht die vorbefuellte Vorgabe wie eine Leistung aus. */}
        <span
          style={{ flex: 1, opacity: set.is_completed ? 1 : 0.55, display: 'flex', flexDirection: 'column', gap: 2 }}
          onClick={!readonly ? () => setEditing(true) : undefined}
        >
          <span className="gewicht">
            {set.weight_kg != null ? `${set.weight_kg} kg` : '\u2014'}
          </span>
          {/* Was das an der Stange bedeutet. Siehe Scheiben.tsx. */}
          <Scheiben kg={set.weight_kg} knapp />
        </span>
        <span
          style={{ flex: 1, opacity: set.is_completed ? 1 : 0.55 }}
          onClick={!readonly ? () => setEditing(true) : undefined}
        >
          <span className="zahl">
            {set.reps != null ? `${set.reps} Wdh` : set.duration_seconds ? `${set.duration_seconds}s` : '\u2014'}
          </span>
        </span>
        <span style={{ width: 50, color: 'var(--text-muted)' }}>
          {set.rpe != null ? `RPE ${set.rpe}` : ''}
        </span>
        {!readonly && (
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            {/* Kein Stift mehr: die Werte selbst sind die Trefferflaeche zum
                Bearbeiten. Das Loeschen bleibt als Knopf erreichbar, der
                Wisch-Weg daneben gibt es nur auf Geraeten mit Touch. */}
            <button className="btn-danger btn-sm" onClick={onDelete} aria-label="Satz löschen">&times;</button>
            {onToggleCompleted && (
              // 44 Pixel: die Flaeche, die sich mit nassen Fingern noch treffen
              // laesst. Das ist der Knopf, der im Gym am oeftesten gedrueckt wird.
              <button
                onClick={onToggleCompleted}
                aria-label={set.is_completed ? 'Haken entfernen' : 'Satz abhaken'}
                aria-pressed={set.is_completed}
                style={{
                  width: 44, height: 44, minWidth: 44,
                  borderRadius: 10,
                  border: `2px solid ${set.is_completed ? 'var(--success)' : 'var(--border)'}`,
                  background: set.is_completed ? 'var(--success)' : 'transparent',
                  color: set.is_completed ? '#fff' : 'var(--border)',
                  fontSize: '1.25rem', fontWeight: 700, lineHeight: 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                {'\u2713'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
