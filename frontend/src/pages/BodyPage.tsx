import { useEffect, useState } from 'react';
import { api } from '../api';
import type { BodyMetric, BodyTrendPoint, MealprepZiele, Aktivitaetsniveau } from '../types';
import ProgressChart from '../components/ProgressChart';
import {
  ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';

// Die Stufen tragen die Namen, die MealPrep fuer seine Faktoren benutzt.
// Angezeigt wird, was sie bedeuten.
const STUFEN_TEXT: Record<string, string> = {
  sedentary: 'Kaum Training',
  light: 'Leicht aktiv',
  moderate: 'Mäßig aktiv',
  active: 'Aktiv',
  very_active: 'Sehr aktiv',
};

export default function BodyPage() {
  const [metrics, setMetrics] = useState<BodyMetric[]>([]);
  const [trend, setTrend] = useState<BodyTrendPoint[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [ziele, setZiele] = useState<MealprepZiele | null>(null);
  const [niveau, setNiveau] = useState<Aktivitaetsniveau | null>(null);

  useEffect(() => { load(); }, []);

  async function load() {
    const [m, t] = await Promise.all([
      api.get<BodyMetric[]>('/body/metrics'),
      api.get<BodyTrendPoint[]>('/body/trend'),
    ]);
    setMetrics(m);
    setTrend(t);

    // Tagesziele aus MealPrep. Das Gewicht von hier ist deren Eingangsgroesse,
    // also gehoert das Ergebnis auch hierhin. Ist MealPrep nicht erreichbar,
    // bleibt die Zeile weg, statt eine Null zu behaupten.
    api.get<MealprepZiele>('/body/mealprep-ziele')
      .then(z => setZiele(z.verfuegbar ? z : null))
      .catch(() => setZiele(null));

    // Das Bindeglied: aus dem Training folgt die Stufe, aus der Stufe der
    // Bedarf. Ohne diese Zeile sieht man nur das Ergebnis und nicht, warum.
    api.get<Aktivitaetsniveau>('/progress/aktivitaetsniveau')
      .then(setNiveau)
      .catch(() => setNiveau(null));
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api.post('/body/metrics', {
      date: fd.get('date'),
      weight_kg: parseFloat(fd.get('weight_kg') as string),
      body_fat_pct: fd.get('body_fat_pct') ? parseFloat(fd.get('body_fat_pct') as string) : null,
      waist_cm: fd.get('waist_cm') ? parseFloat(fd.get('waist_cm') as string) : null,
      notes: fd.get('notes') || null,
    });
    setShowForm(false);
    load();
  }

  async function deleteMetric(id: number) {
    if (!confirm('Messung löschen?')) return;
    await api.del(`/body/metrics/${id}`);
    load();
  }

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="page fade-in">
      <div className="flex-between mb-16">
        <h1>Körperdaten</h1>
        <button className="btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Abbrechen' : '+ Messung'}
        </button>
      </div>

      {niveau && (
        <div className="card mb-16">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>
            Dein Trainingsaufwand bestimmt den Kalorienbedarf
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, opacity: niveau.belastbar ? 1 : 0.5 }}>
              {STUFEN_TEXT[niveau.stufe] ?? niveau.stufe}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Faktor {niveau.faktor}
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {niveau.begruendung}
          </div>
          {niveau.belastbar && !niveau.an_mealprep_uebertragen && (
            <div style={{ fontSize: '0.7rem', color: 'var(--warning)', marginTop: 4 }}>
              Wird nach dem nächsten beendeten Training an MealPrep übertragen
            </div>
          )}
        </div>
      )}

      {ziele && (
        <div className="card mb-16">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>
            Tagesziele aus MealPrep, gerechnet aus Gewicht und Trainingsaufwand
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {ziele.kcal != null && (
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{Math.round(ziele.kcal)}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>kcal</div>
              </div>
            )}
            {ziele.protein_g != null && (
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{Math.round(ziele.protein_g)} g</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Protein</div>
              </div>
            )}
            {ziele.carbs_g != null && (
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{Math.round(ziele.carbs_g)} g</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Kohlenhydrate</div>
              </div>
            )}
            {ziele.fat_g != null && (
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{Math.round(ziele.fat_g)} g</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Fett</div>
              </div>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="card mb-16">
          <div className="row">
            <div className="form-group">
              <label>Datum</label>
              <input type="date" name="date" defaultValue={today} required />
            </div>
            <div className="form-group">
              <label>Gewicht (kg)</label>
              <input type="number" name="weight_kg" step="0.1" required />
            </div>
          </div>
          <div className="row">
            <div className="form-group">
              <label>KFA (%)</label>
              <input type="number" name="body_fat_pct" step="0.1" />
            </div>
            <div className="form-group">
              <label>Bauchumfang (cm)</label>
              <input type="number" name="waist_cm" step="0.1" />
            </div>
          </div>
          <div className="form-group">
            <label>Notizen</label>
            <input name="notes" />
          </div>
          <button type="submit" className="btn-primary" style={{ width: '100%' }}>Speichern</button>
        </form>
      )}

      <h2>Gewichtsverlauf</h2>
      <ProgressChart
        data={trend}
        lines={[
          { key: 'weight_kg', color: 'var(--text-muted)', name: 'Gewicht' },
          { key: 'moving_avg', color: 'var(--primary)', name: '7-Tage-Schnitt' },
        ]}
      />

      {/* Body composition chart with dual Y-axis */}
      {metrics.some(m => m.body_fat_pct != null) && (
        <>
          <h2 className="mt-16">Körperzusammensetzung</h2>
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart
              data={metrics.filter(m => m.body_fat_pct != null).reverse()}
              margin={{ top: 5, right: 5, bottom: 5, left: -10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="date"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickFormatter={v => {
                  const d = new Date(v);
                  return `${d.getDate()}.${d.getMonth() + 1}`;
                }}
              />
              <YAxis yAxisId="weight" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis yAxisId="fat" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--text)',
                }}
              />
              <Legend />
              <Line yAxisId="weight" type="monotone" dataKey="weight_kg" stroke="var(--primary)" name="Gewicht (kg)" dot={false} strokeWidth={2} />
              <Bar yAxisId="fat" dataKey="body_fat_pct" fill="rgba(249,115,22,0.5)" name="KFA (%)" radius={[2, 2, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}

      <div className="mt-16">
        <h2>Messungen</h2>
        {metrics.length === 0 && <div className="empty">Keine Messungen vorhanden</div>}
        {metrics.map(m => (
          <div key={m.id} className="card flex-between">
            <div>
              <strong>{new Date(m.date).toLocaleDateString('de-DE')}</strong>
              <div style={{ fontSize: '0.85rem' }}>
                {m.weight_kg} kg
                {m.body_fat_pct != null && ` • ${m.body_fat_pct}% KFA`}
                {m.waist_cm != null && ` • ${m.waist_cm} cm`}
              </div>
              {m.notes && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{m.notes}</div>}
            </div>
            <button className="btn-danger btn-sm" onClick={() => deleteMetric(m.id)}>&times;</button>
          </div>
        ))}
      </div>
    </div>
  );
}
