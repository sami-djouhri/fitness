import { useEffect, useState } from 'react';
import { api } from '../api';
import type { PlanListItem, Plan, PlanDay, Exercise, Planvorlage } from '../types';
import ExercisePicker from '../components/ExercisePicker';

/**
 * Trainingspläne, jetzt tatsächlich änderbar.
 *
 * ★ Der Befund war: "Es gibt fertige Trainings, die ich nicht anpassen kann."
 * Das Backend konnte es die ganze Zeit (`PUT /plans/day-exercises/{id}` und
 * `PUT /plans/days/{id}`), nur rief das niemand auf. Man konnte Übungen
 * hinzufügen und löschen, aber Sätze, Wiederholungen, Pause und den Namen
 * eines Tages nicht bearbeiten. Ein Plan, den man nicht anpassen kann, wird
 * nicht angepasst, sondern ignoriert.
 *
 * Dazu die Vorlagen: sie erzeugen einen Plan aus der eingetragenen
 * Ausrüstung, statt einen Studio-Plan hinzustellen, den zu Hause niemand
 * ausführen kann.
 */

const WOCHENTAGE = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

export default function PlanPage() {
  const [plaene, setPlaene] = useState<PlanListItem[]>([]);
  const [offen, setOffen] = useState<Plan | null>(null);
  const [vorlagen, setVorlagen] = useState<Planvorlage[]>([]);
  const [waehler, setWaehler] = useState<number | null>(null);
  const [arbeitet, setArbeitet] = useState(false);

  useEffect(() => { ladePlaene(); ladeVorlagen(); }, []);

  async function ladePlaene() {
    setPlaene(await api.get<PlanListItem[]>('/plans'));
  }

  async function ladeVorlagen() {
    try {
      setVorlagen(await api.get<Planvorlage[]>('/plans/vorlagen'));
    } catch { /* Vorlagen sind eine Zugabe, kein Muss. */ }
  }

  async function ladePlan(id: number) {
    setOffen(await api.get<Plan>(`/plans/${id}`));
  }

  async function neuLaden() {
    if (offen) await ladePlan(offen.id);
    await ladePlaene();
  }

  async function ausVorlage(id: string) {
    setArbeitet(true);
    try {
      const plan = await api.post<Plan>(`/plans/vorlagen/${id}`);
      await ladePlaene();
      setOffen(plan);
    } finally {
      setArbeitet(false);
    }
  }

  /* --------------------------------------------------------------- */

  if (offen) {
    return (
      <PlanDetail
        plan={offen}
        onZurueck={() => { setOffen(null); ladePlaene(); }}
        onAenderung={neuLaden}
        waehler={waehler}
        setWaehler={setWaehler}
      />
    );
  }

  return (
    <div className="page fade-in">
      <div className="seiten-kopf">
        <h1>Trainingspläne</h1>
        <button className="btn-primary btn-sm" onClick={async () => {
          const name = prompt('Name des Plans:');
          if (!name) return;
          const p = await api.post<Plan>('/plans', { name });
          await ladePlaene();
          setOffen(p);
        }}>
          + Leerer Plan
        </button>
      </div>

      {plaene.length === 0 && (
        <div className="leer">
          Noch kein Plan. Eine Vorlage unten erzeugt einen, der zu deiner
          Ausrüstung passt.
        </div>
      )}

      {plaene.map((p) => (
        <div key={p.id} className="karte flach" style={{ cursor: 'pointer' }}
             onClick={() => ladePlan(p.id)}>
          <div>
            <strong>{p.name}</strong>
            {p.is_active && <span className="etikett gruen" style={{ marginLeft: 8 }}>aktiv</span>}
            {p.description && <div className="klein gedaempft">{p.description}</div>}
          </div>
          <span className="klein gedaempft">{p.day_count} Tage</span>
        </div>
      ))}

      <h2>Vorlagen</h2>
      <p className="klein gedaempft">
        Eine Vorlage nennt keine festen Übungen, sondern das Ziel je Platz.
        Welche Übung daraus wird, entscheidet deine eingetragene Ausrüstung.
      </p>
      <div className="vorlagen">
        {vorlagen.map((v) => (
          <button key={v.id} className="vorlage" disabled={arbeitet}
                  onClick={() => ausVorlage(v.id)}>
            <strong>
              {v.name}
              {v.passt && <span className="etikett gruen" style={{ marginLeft: 6 }}>passt</span>}
            </strong>
            <span className="klein gedaempft">{v.beschreibung}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function PlanDetail({ plan, onZurueck, onAenderung, waehler, setWaehler }: {
  plan: Plan;
  onZurueck: () => void;
  onAenderung: () => Promise<void>;
  waehler: number | null;
  setWaehler: (v: number | null) => void;
}) {
  return (
    <div className="page fade-in">
      <div className="seiten-kopf">
        <button className="btn-secondary btn-sm" onClick={onZurueck}>&larr; Zurück</button>
        <div style={{ display: 'flex', gap: 6 }}>
          {!plan.is_active && (
            <button className="btn-primary btn-sm" onClick={async () => {
              await api.post(`/plans/${plan.id}/activate`);
              await onAenderung();
            }}>
              Aktivieren
            </button>
          )}
          <button className="btn-danger btn-sm" onClick={async () => {
            if (!confirm('Plan wirklich löschen?')) return;
            await api.del(`/plans/${plan.id}`);
            onZurueck();
          }}>
            Löschen
          </button>
        </div>
      </div>

      <h1>
        {plan.name}
        {plan.is_active && <span className="etikett gruen" style={{ marginLeft: 8 }}>aktiv</span>}
      </h1>
      {plan.description && <p className="klein gedaempft">{plan.description}</p>}

      {plan.days.map((tag) => (
        <Tagkarte key={tag.id} tag={tag} onAenderung={onAenderung}
                  onUebungHinzu={() => setWaehler(tag.id)} />
      ))}

      <button className="btn-secondary" style={{ width: '100%' }} onClick={async () => {
        const name = prompt('Name des Tages, etwa "Push A":');
        if (!name) return;
        await api.post(`/plans/${plan.id}/days`, { name, sort_order: plan.days.length });
        await onAenderung();
      }}>
        + Tag hinzufügen
      </button>

      {waehler !== null && (
        <ExercisePicker
          onSelect={async (ex: Exercise) => {
            const tag = plan.days.find((d) => d.id === waehler);
            await api.post(`/plans/days/${waehler}/exercises`, {
              exercise_id: ex.id,
              sort_order: tag?.exercises.length ?? 0,
              target_sets: 3,
              // Der Katalog kennt den sinnvollen Bereich je Übung. Feste 8
              // bis 12 ergaben bei Waden und Kreuzheben denselben Unsinn.
              target_reps_min: ex.wdh_min ?? 8,
              target_reps_max: ex.wdh_max ?? 12,
              rest_seconds: ex.pause_s ?? 90,
            });
            setWaehler(null);
            await onAenderung();
          }}
          onClose={() => setWaehler(null)}
        />
      )}
    </div>
  );
}

function Tagkarte({ tag, onAenderung, onUebungHinzu }: {
  tag: PlanDay;
  onAenderung: () => Promise<void>;
  onUebungHinzu: () => void;
}) {
  const [name, setName] = useState(tag.name);
  useEffect(() => setName(tag.name), [tag.name]);

  async function tagSpeichern(felder: Partial<PlanDay>) {
    await api.put(`/plans/days/${tag.id}`, felder);
    await onAenderung();
  }

  return (
    <div className="karte">
      <div className="tagkopf">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => { if (name && name !== tag.name) tagSpeichern({ name }); }}
          aria-label="Name des Tages"
        />
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn-secondary btn-sm" onClick={onUebungHinzu}>+ Übung</button>
          <button className="btn-danger btn-sm" onClick={async () => {
            if (!confirm(`Tag "${tag.name}" löschen?`)) return;
            await api.del(`/plans/days/${tag.id}`);
            await onAenderung();
          }}>&times;</button>
        </div>
      </div>

      {/* Fester Wochentag oder Rotation. Ohne diese Wahl war das Feld
          gepflegt und wurde nie gelesen: der Plan hatte seit dem 01.03.
          Wochentage, die nirgends auftauchten. */}
      <div className="wochentagwahl">
        <button className={tag.day_of_week == null ? 'aktiv' : ''}
                onClick={() => tagSpeichern({ day_of_week: null })}>
          rotierend
        </button>
        {WOCHENTAGE.map((t, i) => (
          <button key={t} className={tag.day_of_week === i ? 'aktiv' : ''}
                  onClick={() => tagSpeichern({ day_of_week: i })}>
            {t}
          </button>
        ))}
      </div>

      {tag.exercises.length === 0 && (
        <div className="klein gedaempft">Noch keine Übungen.</div>
      )}

      {tag.exercises.map((pe, i) => (
        <Uebungszeile key={pe.id} pe={pe} nummer={i + 1} onAenderung={onAenderung} />
      ))}
    </div>
  );
}

function Uebungszeile({ pe, nummer, onAenderung }: {
  pe: PlanDay['exercises'][number];
  nummer: number;
  onAenderung: () => Promise<void>;
}) {
  const [saetze, setSaetze] = useState(String(pe.target_sets));
  const [unten, setUnten] = useState(String(pe.target_reps_min));
  const [oben, setOben] = useState(String(pe.target_reps_max));
  const [pause, setPause] = useState(String(pe.rest_seconds));

  useEffect(() => {
    setSaetze(String(pe.target_sets));
    setUnten(String(pe.target_reps_min));
    setOben(String(pe.target_reps_max));
    setPause(String(pe.rest_seconds));
  }, [pe.target_sets, pe.target_reps_min, pe.target_reps_max, pe.rest_seconds]);

  async function speichern() {
    const neu = {
      target_sets: parseInt(saetze, 10),
      target_reps_min: parseInt(unten, 10),
      target_reps_max: parseInt(oben, 10),
      rest_seconds: parseInt(pause, 10),
    };
    if (Object.values(neu).some((v) => Number.isNaN(v))) return;
    if (neu.target_sets === pe.target_sets && neu.target_reps_min === pe.target_reps_min
        && neu.target_reps_max === pe.target_reps_max
        && neu.rest_seconds === pe.rest_seconds) return;
    await api.put(`/plans/day-exercises/${pe.id}`, neu);
    await onAenderung();
  }

  return (
    <div className="planzeile">
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '0.88rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {nummer}. {pe.exercise_name}
        </div>
      </div>
      <div className="planzeile-werte" onBlur={speichern}>
        <input value={saetze} onChange={(e) => setSaetze(e.target.value)}
               inputMode="numeric" aria-label="Sätze" title="Sätze" />
        <span>x</span>
        <input value={unten} onChange={(e) => setUnten(e.target.value)}
               inputMode="numeric" aria-label="Wiederholungen von" title="Wiederholungen von" />
        <span>-</span>
        <input value={oben} onChange={(e) => setOben(e.target.value)}
               inputMode="numeric" aria-label="Wiederholungen bis" title="Wiederholungen bis" />
        <input value={pause} onChange={(e) => setPause(e.target.value)}
               inputMode="numeric" aria-label="Pause in Sekunden" title="Pause in Sekunden" />
        <span className="klein gedaempft">s</span>
      </div>
      <button className="btn-danger btn-sm" onClick={async () => {
        await api.del(`/plans/day-exercises/${pe.id}`);
        await onAenderung();
      }}>&times;</button>
    </div>
  );
}
