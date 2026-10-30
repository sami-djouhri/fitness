import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ReadinessAnalyticsResponse } from '../types';

const FATIGUE_EMOJIS: Record<number, string> = {
  1: '\u{1F4AA}', // Frisch
  2: '\u{1F60A}', // Gut
  3: '\u{1F610}', // Normal
  4: '\u{1F634}', // Muede
  5: '\u{1F635}', // Erschoepft
};

const SLEEP_EMOJIS: Record<number, string> = {
  1: '\u{1F62B}', // Schlecht
  2: '\u{1F615}', // Maessig
  3: '\u{1F610}', // OK
  4: '\u{1F60C}', // Gut
  5: '\u{1F31F}', // Sehr gut
};

const MOTIVATION_EMOJIS: Record<number, string> = {
  1: '\u{1F612}', // Niedrig
  2: '\u{1F614}', // Gering
  3: '\u{1F610}', // Mittel
  4: '\u{1F642}', // Hoch
  5: '\u{1F525}', // Max
};

function getEmoji(map: Record<number, string>, value: number): string {
  const rounded = Math.round(value);
  return map[rounded] || map[3];
}

function formatVolume(v: number | null): string {
  if (v === null) return '---';
  return Math.round(v).toLocaleString('de') + ' kg';
}

export default function ReadinessInsights() {
  const [data, setData] = useState<ReadinessAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<ReadinessAnalyticsResponse>('/progress/readiness?days=30')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 16 }}>
        <div className="skeleton" style={{ height: 120, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 80, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 80 }} />
      </div>
    );
  }

  if (!data) {
    return <div className="empty">Fehler beim Laden der Bereitschaftsdaten</div>;
  }

  const total = data.workouts_with_readiness + data.workouts_without_readiness;

  if (data.workouts_with_readiness === 0) {
    return (
      <div className="empty">
        Noch keine Bereitschaftsdaten vorhanden.<br />
        Fuelle den Bereitschafts-Check vor deinem naechsten Training aus.
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Coverage stats */}
      <div className="stat-grid mb-16">
        <div className="stat-card">
          <div className="value">{data.workouts_with_readiness}</div>
          <div className="label">Mit Check</div>
        </div>
        <div className="stat-card">
          <div className="value">
            {total > 0 ? Math.round((data.workouts_with_readiness / total) * 100) : 0}%
          </div>
          <div className="label">Abdeckung</div>
        </div>
      </div>

      {/* Sleep correlation */}
      <h2>Schlaf-Korrelation</h2>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <div
          className="card"
          style={{
            flex: 1,
            borderLeft: '3px solid var(--success)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Guter Schlaf (&ge;4)
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--success)' }}>
            {formatVolume(data.sleep_correlation.high_avg_volume)}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            &Oslash; Volumen ({data.sleep_correlation.high_workout_count} Workouts)
          </div>
        </div>
        <div
          className="card"
          style={{
            flex: 1,
            borderLeft: '3px solid var(--danger)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Schlechter Schlaf (&le;2)
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--danger)' }}>
            {formatVolume(data.sleep_correlation.low_avg_volume)}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            &Oslash; Volumen ({data.sleep_correlation.low_workout_count} Workouts)
          </div>
        </div>
      </div>

      {/* Fatigue correlation */}
      <h2>Erschoepfungs-Korrelation</h2>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <div
          className="card"
          style={{
            flex: 1,
            borderLeft: '3px solid var(--success)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Geringe Erschoepfung (&le;2)
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--success)' }}>
            {formatVolume(data.fatigue_correlation.low_avg_volume)}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            &Oslash; Volumen ({data.fatigue_correlation.low_workout_count} Workouts)
          </div>
        </div>
        <div
          className="card"
          style={{
            flex: 1,
            borderLeft: '3px solid var(--danger)',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            Hohe Erschoepfung (&ge;4)
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--danger)' }}>
            {formatVolume(data.fatigue_correlation.high_avg_volume)}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            &Oslash; Volumen ({data.fatigue_correlation.high_workout_count} Workouts)
          </div>
        </div>
      </div>

      {/* Trend table */}
      <h2>Bereitschafts-Verlauf</h2>
      {data.daily_averages.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.85rem',
          }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '8px 6px', color: 'var(--text-muted)', fontWeight: 500 }}>
                  Datum
                </th>
                <th style={{ textAlign: 'center', padding: '8px 6px', color: 'var(--text-muted)', fontWeight: 500 }}>
                  Erschoepfung
                </th>
                <th style={{ textAlign: 'center', padding: '8px 6px', color: 'var(--text-muted)', fontWeight: 500 }}>
                  Schlaf
                </th>
                <th style={{ textAlign: 'center', padding: '8px 6px', color: 'var(--text-muted)', fontWeight: 500 }}>
                  Motivation
                </th>
              </tr>
            </thead>
            <tbody>
              {data.daily_averages.slice().reverse().map(day => (
                <tr
                  key={day.date}
                  style={{ borderBottom: '1px solid var(--border)' }}
                >
                  <td style={{ padding: '8px 6px' }}>
                    {new Date(day.date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })}
                  </td>
                  <td style={{ textAlign: 'center', padding: '8px 6px', fontSize: '1.1rem' }}>
                    {getEmoji(FATIGUE_EMOJIS, day.avg_fatigue)}
                  </td>
                  <td style={{ textAlign: 'center', padding: '8px 6px', fontSize: '1.1rem' }}>
                    {getEmoji(SLEEP_EMOJIS, day.avg_sleep)}
                  </td>
                  <td style={{ textAlign: 'center', padding: '8px 6px', fontSize: '1.1rem' }}>
                    {getEmoji(MOTIVATION_EMOJIS, day.avg_motivation)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">Keine Tages-Daten vorhanden</div>
      )}
    </div>
  );
}
