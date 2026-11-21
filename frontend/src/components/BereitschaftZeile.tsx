import { useState } from 'react';

/**
 * Der Bereitschafts-Check als freiwillige Zeile im laufenden Training.
 *
 * Bis 2026-11-21 stand er als eigener Bildschirm zwischen „Starten“ und dem
 * ersten Satz. Gemessen hatten drei von fünf Trainings einen Check, und jeder
 * Start kostete einen Bildschirm mehr. Jetzt startet ein Tipp das Training,
 * und wer mag, tippt hier drei Werte an. Jeder Tipp wird sofort gespeichert,
 * es gibt keinen Absenden-Knopf, den man vergessen kann.
 */

interface Werte {
  fatigue_level: number | null;
  sleep_quality: number | null;
  motivation: number | null;
}

interface Props {
  werte: Werte;
  onWert: (feld: keyof Werte, wert: number) => void;
  onSchliessen: () => void;
}

const SKALEN: { feld: keyof Werte; titel: string; stufen: [string, string][] }[] = [
  { feld: 'fatigue_level', titel: 'Körper', stufen: [['\u{1F4AA}', 'Frisch'], ['\u{1F60A}', 'Gut'], ['\u{1F610}', 'Normal'], ['\u{1F634}', 'Müde'], ['\u{1F635}', 'Erschöpft']] },
  { feld: 'sleep_quality', titel: 'Schlaf', stufen: [['\u{1F62B}', 'Schlecht'], ['\u{1F615}', 'Mäßig'], ['\u{1F610}', 'OK'], ['\u{1F60C}', 'Gut'], ['\u{1F31F}', 'Sehr gut']] },
  { feld: 'motivation', titel: 'Lust', stufen: [['\u{1F612}', 'Niedrig'], ['\u{1F614}', 'Gering'], ['\u{1F610}', 'Mittel'], ['\u{1F642}', 'Hoch'], ['\u{1F525}', 'Max']] },
];

export default function BereitschaftZeile({ werte, onWert, onSchliessen }: Props) {
  const [offen, setOffen] = useState(false);

  if (!offen) {
    return (
      <div className="card bereitschaft-zeile" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <button className="btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => setOffen(true)}>
          Wie fühlst du dich? (freiwillig)
        </button>
        <button className="btn-secondary btn-sm" onClick={onSchliessen} aria-label="Nicht jetzt">×</button>
      </div>
    );
  }

  return (
    <div className="card bereitschaft-zeile" style={{ marginBottom: 12 }}>
      {SKALEN.map(({ feld, titel, stufen }) => (
        <div key={feld} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <span className="klein gedaempft" style={{ width: 44, flexShrink: 0 }}>{titel}</span>
          {stufen.map(([zeichen, wort], i) => {
            const wert = i + 1;
            const gewaehlt = werte[feld] === wert;
            return (
              <button
                key={wert}
                onClick={() => onWert(feld, wert)}
                aria-label={`${titel}: ${wort}`}
                aria-pressed={gewaehlt}
                title={wort}
                style={{
                  flex: '1 1 0', minWidth: 0, padding: 0, minHeight: 44, fontSize: '1.2rem', borderRadius: 'var(--radius)',
                  background: gewaehlt ? 'var(--primary)' : 'var(--bg-input)',
                  border: gewaehlt ? '2px solid var(--primary)' : '2px solid transparent',
                  cursor: 'pointer',
                }}
              >
                {zeichen}
              </button>
            );
          })}
        </div>
      ))}
      <button className="btn-secondary btn-sm" style={{ width: '100%' }} onClick={onSchliessen}>Fertig</button>
    </div>
  );
}
