import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, Legend,
} from 'recharts';
import { api } from '../api';
import type {
  Gruppenwoche, PersonalRecord, VolumeSummary, CalendarDay,
  Schritteuebersicht, Exercise, StrengthLevel, Progressionsvorschlag,
} from '../types';

/**
 * Zahlen statt Abzeichen.
 *
 * Diese Seite ersetzt den Erfolge-Tab. Der zeigte 18 Auszeichnungen, von
 * denen zwei freigeschaltet waren, und sagte über das Training nichts aus.
 * Was hier steht, ist messbar und handlungsleitend: wie viel Volumen jede
 * Muskelgruppe abbekommt, gemessen am Bereich, in dem sie wächst.
 */

type Abschnitt = 'woche' | 'verlauf' | 'kraft' | 'alltag';

const BEWERTUNGSFARBE: Record<string, string> = {
  unter_mv: '#ef4444',
  erhaltung: '#f97316',
  unter_mev: '#facc15',
  im_korridor: '#22c55e',
  ueber_mav: '#38bdf8',
  ueber_mrv: '#a855f7',
};

const BEWERTUNGSTEXT: Record<string, string> = {
  unter_mv: 'zu wenig',
  erhaltung: 'hält nur',
  unter_mev: 'wirkt',
  im_korridor: 'im besten Bereich',
  ueber_mav: 'viel',
  ueber_mrv: 'zu viel',
};

export default function ZahlenPage() {
  const [abschnitt, setAbschnitt] = useState<Abschnitt>('woche');
  const [woche, setWoche] = useState<Gruppenwoche[]>([]);
  const [verlauf, setVerlauf] = useState<{ woche: string; gruppen: Record<string, number> }[]>([]);
  const [volumen, setVolumen] = useState<VolumeSummary[]>([]);
  const [prs, setPrs] = useState<PersonalRecord[]>([]);
  const [kalender, setKalender] = useState<CalendarDay[]>([]);
  const [schritte, setSchritte] = useState<Schritteuebersicht | null>(null);
  const [uebungen, setUebungen] = useState<Exercise[]>([]);
  const [gewaehlteUebung, setGewaehlteUebung] = useState<number | null>(null);
  const [kraftstand, setKraftstand] = useState<StrengthLevel | null>(null);
  const [progression, setProgression] = useState<Progressionsvorschlag | null>(null);

  useEffect(() => {
    api.get<Gruppenwoche[]>('/analyse/volumen').then(setWoche).catch(() => {});
    api.get<typeof verlauf>('/analyse/verlauf?wochen=8').then(setVerlauf).catch(() => {});
    api.get<VolumeSummary[]>('/progress/volume').then(setVolumen).catch(() => {});
    api.get<PersonalRecord[]>('/progress/prs/recent').then(setPrs).catch(() => {});
    api.get<CalendarDay[]>('/progress/calendar?months=3').then(setKalender).catch(() => {});
    api.get<Schritteuebersicht>('/schritte?tage=30').then(setSchritte).catch(() => {});
    api.get<Exercise[]>('/exercises?limit=300').then(setUebungen).catch(() => {});
  }, []);

  useEffect(() => {
    if (!gewaehlteUebung) { setKraftstand(null); setProgression(null); return; }
    api.get<StrengthLevel>(`/progress/strength-level?exercise_id=${gewaehlteUebung}`)
      .then(setKraftstand).catch(() => setKraftstand(null));
    api.get<Progressionsvorschlag>(`/exercises/${gewaehlteUebung}/progression`)
      .then(setProgression).catch(() => setProgression(null));
  }, [gewaehlteUebung]);

  const gesamtSaetze = woche.reduce((s, g) => s + g.direkt, 0);

  /**
   * Sortiert nach Dringlichkeit statt nach Registry-Reihenfolge.
   *
   * ★ Nach der ersten visuellen Prüfung geändert: die Seite listete bei
   * leerer Woche siebzehn rote Zeilen "zu wenig" untereinander, alle mit
   * demselben Inhalt. Das liest niemand, und es sagt auch nichts: eine Woche
   * ohne Training ist überall null. Jetzt steht oben, was tatsächlich
   * bearbeitet gehört, und Gruppen ohne jede Arbeit werden zusammengefasst,
   * solange fast nichts erfasst ist.
   */
  const wochenrelevant = useMemo(() => {
    const rang: Record<string, number> = {
      ueber_mrv: 0, unter_mv: 1, erhaltung: 2, unter_mev: 3,
      ueber_mav: 4, im_korridor: 5,
    };
    return woche
      .filter((g) => g.direkt > 0 || g.mev > 0)
      .sort((a, b) => {
        // Gruppen mit Arbeit zuerst, dann nach Dringlichkeit der Bewertung.
        if ((a.direkt > 0) !== (b.direkt > 0)) return a.direkt > 0 ? -1 : 1;
        const r = (rang[a.bewertung] ?? 9) - (rang[b.bewertung] ?? 9);
        return r !== 0 ? r : b.direkt - a.direkt;
      });
  }, [woche]);

  /** Fast nichts erfasst: dann ist die Mängelliste keine Auskunft. */
  const nochAmAnfang = gesamtSaetze < 5;
  const angezeigt = nochAmAnfang
    ? wochenrelevant.filter((g) => g.direkt > 0)
    : wochenrelevant;
  const ohneArbeit = wochenrelevant.length - angezeigt.length;
  const imKorridor = woche.filter((g) => g.bewertung === 'im_korridor').length;
  const zuWenig = woche.filter(
    (g) => g.mev > 0 && (g.bewertung === 'unter_mv' || g.bewertung === 'erhaltung')).length;
  const zuViel = woche.filter((g) => g.bewertung === 'ueber_mrv').length;

  return (
    <div className="page fade-in">
      <h1>Zahlen</h1>

      <div className="kennzahlen">
        <Kennzahl wert={Math.round(gesamtSaetze)} text="harte Sätze, 7 Tage" />
        <Kennzahl wert={angezeigt.length} text="Gruppen trainiert" />
        {/* ★ "17 unterversorgt" stand bei leerer Woche ganz oben in Orange.
            Das ist keine Auskunft, sondern eine Selbstverständlichkeit: wer
            nicht trainiert hat, hat überall zu wenig. */}
        {!nochAmAnfang && (
          <>
            <Kennzahl wert={imKorridor} text="im besten Bereich" farbe="#22c55e" />
            <Kennzahl wert={zuWenig} text="unterversorgt"
                      farbe={zuWenig > 0 ? '#f97316' : undefined} />
            {zuViel > 0 && (
              <Kennzahl wert={zuViel} text="über der Grenze" farbe="#a855f7" />
            )}
          </>
        )}
      </div>

      <div className="segment breit">
        {([['woche', 'Diese Woche'], ['verlauf', 'Verlauf'],
           ['kraft', 'Kraft'], ['alltag', 'Alltag']] as [Abschnitt, string][])
          .map(([k, t]) => (
            <button key={k} className={abschnitt === k ? 'aktiv' : ''}
                    onClick={() => setAbschnitt(k)}>{t}</button>
          ))}
      </div>

      {/* ---------------------------------------------------------- Woche */}
      {abschnitt === 'woche' && (
        <>
          <p className="gedaempft klein">
            Gezählt werden Sätze nahe am Muskelversagen. Der grüne Bereich ist
            der, in dem am meisten wächst; die Grenzen stammen aus den
            Volumen-Landmarks und sind Richtwerte, keine Vorgaben.
          </p>
          {angezeigt.length === 0 && (
            <div className="leer">
              Diese Woche noch keine Sätze. Sobald du trainierst, steht hier je
              Muskelgruppe, wie viel angekommen ist und wo der wirksame Bereich
              liegt.
            </div>
          )}
          {angezeigt.map((g) => (
            <div key={g.gruppe} className="volumenzeile">
              <div className="volumenzeile-kopf">
                <strong>{g.name}</strong>
                <span className="etikett"
                      style={{ background: BEWERTUNGSFARBE[g.bewertung] }}>
                  {BEWERTUNGSTEXT[g.bewertung]}
                </span>
              </div>
              <VolumenBalken g={g} />
              <div className="klein gedaempft">
                {g.direkt.toFixed(0)} direkt
                {g.gewichtet > g.direkt && (
                  <> &middot; {g.gewichtet.toFixed(1)} mit Mitarbeit</>
                )}
                {g.volumen_kg > 0 && (
                  <> &middot; {Math.round(g.volumen_kg).toLocaleString('de')} kg</>
                )}
              </div>
              <div className="klein">{g.hinweis}</div>
            </div>
          ))}
          {nochAmAnfang && ohneArbeit > 0 && (
            <p className="klein gedaempft" style={{ marginTop: 10 }}>
              {ohneArbeit} weitere Gruppen hatten diese Woche nichts. Sie
              erscheinen hier einzeln, sobald genug erfasst ist, um eine
              Aussage daraus zu machen.
            </p>
          )}
        </>
      )}

      {/* -------------------------------------------------------- Verlauf */}
      {abschnitt === 'verlauf' && (
        <>
          <h2>Sätze je Woche</h2>
          {verlauf.length === 0 && <div className="leer">Noch kein Verlauf.</div>}
          {verlauf.length > 0 && (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={verlaufFuerDiagramm(verlauf)}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="woche" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip contentStyle={diagrammKasten} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="gesamt" name="Sätze gesamt"
                      stroke="var(--primary)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}

          <h2>Volumen je Woche</h2>
          {volumen.length === 0 && <div className="leer">Noch kein Volumen erfasst.</div>}
          {volumen.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={volumen}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="week_start" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip contentStyle={diagrammKasten} />
                <Bar dataKey="total_volume" name="kg" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}

          <h2>Trainingstage</h2>
          <Heatmap tage={kalender} />
        </>
      )}

      {/* ----------------------------------------------------------- Kraft */}
      {abschnitt === 'kraft' && (
        <>
          <h2>Übung ansehen</h2>
          <select
            value={gewaehlteUebung ?? ''}
            onChange={(e) => setGewaehlteUebung(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Übung wählen...</option>
            {uebungen.map((ex) => (
              <option key={ex.id} value={ex.id}>{ex.name}</option>
            ))}
          </select>

          {progression && (
            <div className="karte">
              <strong>Nächstes Mal</strong>
              <div className="vorschlagszeile">
                {progression.gewicht_kg != null && (
                  <span className="grossezahl">{progression.gewicht_kg} kg</span>
                )}
                {progression.wdh != null && (
                  <span className="grossezahl">
                    {progression.wdh}
                    <span className="einheit">
                      {progression.exercise_name.includes('Plank') ? ' s' : ' Wdh'}
                    </span>
                  </span>
                )}
              </div>
              <p className="klein">{progression.begruendung}</p>
              {progression.e1rm != null && (
                <div className="klein gedaempft">
                  Geschätztes Maximum: {progression.e1rm} kg
                  {progression.e1rm_unsicher && (
                    <span className="warnung">
                      {' '}(aus vielen Wiederholungen geschätzt, daher unscharf)
                    </span>
                  )}
                </div>
              )}
              {progression.aufwaermsaetze.length > 0 && (
                <div className="klein gedaempft">
                  Aufwärmen:{' '}
                  {progression.aufwaermsaetze
                    .map((s) => `${s.gewicht_kg} kg x ${s.wdh}`)
                    .join(' , ')}
                </div>
              )}
            </div>
          )}

          {kraftstand && kraftstand.current_1rm != null && (
            <div className="karte">
              <strong>Einordnung: {kraftstand.level}</strong>
              <div className="klein gedaempft">
                {kraftstand.current_1rm.toFixed(1)} kg bei{' '}
                {kraftstand.body_weight?.toFixed(1)} kg Körpergewicht
                {kraftstand.ratio != null && <> ({kraftstand.ratio.toFixed(2)}-faches)</>}
              </div>
              <div className="stufenleiste">
                {Object.entries(kraftstand.levels).map(([stufe, faktor]) => (
                  <span key={stufe}
                        className={`stufe ${kraftstand.level === stufe ? 'aktiv' : ''}`}>
                    {stufe}
                    <em>{((kraftstand.body_weight ?? 80) * faktor).toFixed(0)} kg</em>
                  </span>
                ))}
              </div>
            </div>
          )}

          <h2>Rekorde</h2>
          {prs.length === 0 && <div className="leer">Noch keine Rekorde.</div>}
          {prs.map((pr) => (
            <div key={pr.id} className="karte flach">
              <div>
                <strong>{pr.exercise_name}</strong>
                <div className="klein gedaempft">{rekordText(pr)}</div>
              </div>
              <span className="klein gedaempft">
                {new Date(pr.achieved_at).toLocaleDateString('de-DE')}
              </span>
            </div>
          ))}
        </>
      )}

      {/* ---------------------------------------------------------- Alltag */}
      {abschnitt === 'alltag' && (
        <>
          <h2>Schritte</h2>
          {!schritte || schritte.erfasste_tage === 0 ? (
            <div className="leer">
              Noch keine Schritte übertragen. Die Android-App schiebt sie,
              sobald sie im Heimnetz ist.
            </div>
          ) : (
            <>
              <div className="kennzahlen">
                <Kennzahl wert={schritte.heute ?? 0} text="heute" />
                <Kennzahl wert={schritte.schnitt ?? 0} text="Schnitt" />
                <Kennzahl wert={schritte.aktive_tage} text="aktive Tage" />
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={schritte.tage}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="datum" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip contentStyle={diagrammKasten} />
                  <Bar dataKey="schritte" fill="#38bdf8" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */

const diagrammKasten = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  color: 'var(--text)',
  fontSize: 12,
};

function Kennzahl({ wert, text, farbe }: { wert: number; text: string; farbe?: string }) {
  return (
    <div className="kennzahl">
      <div className="kennzahl-wert" style={farbe ? { color: farbe } : undefined}>
        {wert.toLocaleString('de')}
      </div>
      <div className="kennzahl-text">{text}</div>
    </div>
  );
}

/**
 * Ein Balken, der den Korridor zeigt statt nur einen Wert.
 *
 * ★ Ein reiner Wert ohne Bezug sagt nichts: "14 Sätze" ist für den
 * Latissimus wenig und für den unteren Rücken zu viel. Deshalb steht der
 * Bereich im Bild und der Wert darin.
 */
function VolumenBalken({ g }: { g: Gruppenwoche }) {
  const max = Math.max(g.mrv, g.direkt, 1) * 1.1;
  const p = (n: number) => `${Math.min(100, (n / max) * 100)}%`;
  return (
    <div className="volumenbalken">
      <div className="vb-korridor" style={{ left: p(g.mav_min), width: p(g.mav_max - g.mav_min) }} />
      <div className="vb-grenze" style={{ left: p(g.mrv) }} title={`Grenze ${g.mrv}`} />
      {g.mev > 0 && (
        <div className="vb-schwelle" style={{ left: p(g.mev) }} title={`Wirksam ab ${g.mev}`} />
      )}
      <div className="vb-ist" style={{
        width: p(g.direkt),
        background: BEWERTUNGSFARBE[g.bewertung],
      }} />
    </div>
  );
}

function verlaufFuerDiagramm(
  verlauf: { woche: string; gruppen: Record<string, number> }[],
) {
  return verlauf.map((w) => ({
    woche: new Date(w.woche).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }),
    gesamt: Object.values(w.gruppen).reduce((s, n) => s + n, 0),
  }));
}

function rekordText(pr: PersonalRecord): string {
  const namen: Record<string, string> = {
    '1rm': 'Geschätztes Maximum',
    max_weight: 'Höchstes Gewicht',
    max_reps: 'Meiste Wiederholungen',
    max_volume: 'Größtes Satzvolumen',
  };
  const wert = pr.pr_type === 'max_reps'
    ? `${pr.value} Wdh`
    : `${pr.value.toFixed(1)} kg`;
  return `${namen[pr.pr_type] ?? pr.pr_type}: ${wert}`;
}

function Heatmap({ tage }: { tage: CalendarDay[] }) {
  if (tage.length === 0) return <div className="leer">Noch keine Trainingstage.</div>;
  const proTag: Record<string, CalendarDay> = {};
  for (const t of tage) proTag[t.date] = t;

  const heute = new Date();
  const start = new Date(heute);
  start.setDate(start.getDate() - 90);
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7));

  const wochen: { schluessel: string; saetze: number }[][] = [];
  let aktuell = new Date(start);
  let woche: { schluessel: string; saetze: number }[] = [];
  while (aktuell <= heute) {
    const schluessel = aktuell.toISOString().split('T')[0];
    woche.push({ schluessel, saetze: proTag[schluessel]?.sets ?? 0 });
    if (woche.length === 7) { wochen.push(woche); woche = []; }
    aktuell.setDate(aktuell.getDate() + 1);
  }
  if (woche.length) wochen.push(woche);

  const maxSaetze = Math.max(...tage.map((t) => t.sets), 1);
  const farbe = (s: number) => {
    if (s === 0) return 'var(--bg-card)';
    const i = s / maxSaetze;
    if (i < 0.25) return '#064e3b';
    if (i < 0.5) return '#059669';
    if (i < 0.75) return '#34d399';
    return '#6ee7b7';
  };

  return (
    <div className="heatmap">
      {wochen.map((w, i) => (
        <div key={i} className="heatmap-woche">
          {w.map((t) => (
            <div key={t.schluessel} className="heatmap-tag"
                 style={{ background: farbe(t.saetze) }}
                 title={`${new Date(t.schluessel).toLocaleDateString('de-DE')}: ${t.saetze} Sätze`} />
          ))}
        </div>
      ))}
    </div>
  );
}
