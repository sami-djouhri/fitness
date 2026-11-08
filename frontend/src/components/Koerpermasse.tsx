import { useEffect, useState } from 'react';
import { api } from '../api';

/**
 * Koerpermasse (seit 2026-11-07): letzter Stand mit Veraenderung und ein
 * Messdurchgang Schritt fuer Schritt. Liste und Anleitung kommen vom Dienst
 * (`app/services/koerpermasse.py`), dieselben wie in der App.
 */

interface Massdefinition { id: string; name: string; anleitung: string; seite: string; bereich: string }
interface MassStand { wert_cm: number; datum: string; vorher_cm: number | null; vorher_datum: string | null }
interface Koerpermasse { allgemein: string; definitionen: Massdefinition[]; aktuell: Record<string, MassStand> }

const cm = (v: number) => `${v.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} cm`;
const lies = (s: string | undefined) => {
  const v = parseFloat((s ?? '').replace(',', '.'));
  return Number.isFinite(v) && v >= 10 && v <= 250 ? v : null;
};

export default function KoerpermasseBereich() {
  const [daten, setDaten] = useState<Koerpermasse | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  // null = kein Durchgang, -1 = Einleitung, 0..n-1 = Mass, n = Abschluss
  const [schritt, setSchritt] = useState<number | null>(null);
  const [eingaben, setEingaben] = useState<Record<string, string>>({});
  const [speichert, setSpeichert] = useState(false);

  useEffect(() => {
    api.get<Koerpermasse>('/body/masse').then(setDaten).catch((e) => setFehler(String(e)));
  }, []);

  if (fehler) return <div className="card mb-16"><h3>Maße</h3><p className="warnung">{fehler}</p></div>;
  if (!daten) return null;

  const defs = daten.definitionen;
  const gueltig = Object.fromEntries(
    Object.entries(eingaben).map(([k, v]) => [k, lies(v)]).filter(([, v]) => v !== null),
  ) as Record<string, number>;

  async function speichern() {
    setSpeichert(true);
    try {
      const heute = new Date().toLocaleDateString('sv-SE');
      setDaten(await api.put<Koerpermasse>('/body/masse', { datum: heute, werte: gueltig }));
      setSchritt(null);
      setEingaben({});
    } catch (e) {
      setFehler(String(e));
    } finally {
      setSpeichert(false);
    }
  }

  if (schritt !== null) {
    const ende = schritt >= defs.length;
    const d = !ende && schritt >= 0 ? defs[schritt] : null;
    const text = d ? eingaben[d.id] ?? '' : '';
    return (
      <div className="card mb-16">
        <h3>
          {schritt < 0 ? 'Maße nehmen' : ende ? 'Fertig' : `${schritt + 1}/${defs.length} · ${d!.name}`}
        </h3>
        {schritt < 0 && <p>{daten.allgemein} Du brauchst ein Maßband. Jedes Maß lässt sich überspringen.</p>}
        {d && (
          <>
            <p>{d.anleitung}</p>
            <input
              type="number" inputMode="decimal" step="0.1" autoFocus
              value={text}
              placeholder={daten.aktuell[d.id] ? `zuletzt ${cm(daten.aktuell[d.id].wert_cm)}` : 'cm'}
              onChange={(e) => setEingaben({ ...eingaben, [d.id]: e.target.value })}
              onKeyDown={(e) => { if (e.key === 'Enter') setSchritt(schritt + 1); }}
            />
            {text && lies(text) === null && <p className="warnung klein">Zwischen 10 und 250 cm</p>}
          </>
        )}
        {ende && <p>{Object.keys(gueltig).length ? `${Object.keys(gueltig).length} Maße werden gespeichert.` : 'Nichts eingetragen.'}</p>}
        <div className="flex-between" style={{ marginTop: 12 }}>
          <div>
            {schritt > 0 && <button className="btn-sm" onClick={() => setSchritt(schritt - 1)}>Zurück</button>}{' '}
            <button className="btn-sm" onClick={() => { setSchritt(null); setEingaben({}); }}>Abbrechen</button>
          </div>
          {ende ? (
            <button className="btn-primary" disabled={speichert || !Object.keys(gueltig).length} onClick={speichern}>Speichern</button>
          ) : (
            <button className="btn-primary" onClick={() => setSchritt(schritt + 1)}>
              {schritt < 0 ? 'Los' : text ? 'Weiter' : 'Überspringen'}
            </button>
          )}
        </div>
      </div>
    );
  }

  const gemessen = defs.filter((d) => daten.aktuell[d.id]);
  return (
    <div className="card mb-16">
      <div className="flex-between">
        <h3>Maße</h3>
        <button className="btn-primary btn-sm" onClick={() => setSchritt(-1)}>
          {gemessen.length ? 'Neu messen' : 'Jetzt messen'}
        </button>
      </div>
      {!gemessen.length && <p className="gedaempft">Noch nichts gemessen. Ein Durchgang dauert etwa fünf Minuten.</p>}
      {gemessen.map((d) => {
        const a = daten.aktuell[d.id];
        const diff = a.vorher_cm != null ? a.wert_cm - a.vorher_cm : null;
        return (
          <div key={d.id} className="flex-between">
            <span>{d.name}</span>
            <span>
              {cm(a.wert_cm)}
              {diff != null && (
                <span className="klein gedaempft"> {diff >= 0 ? '+' : '−'}{Math.abs(diff).toLocaleString('de-DE', { maximumFractionDigits: 1 })}</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
