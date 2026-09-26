import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { Ausruestungsluecke, Geraet, Profil, Vorlage } from '../types';

/**
 * Ausrüstung, Ziel und Körperdaten an einem Ort.
 *
 * ★ Diese Seite ist der Grund, warum die App aufhören kann, Beinpresse
 * vorzuschlagen. Vorher gab es keinen Ort, an dem stand, was jemand
 * überhaupt besitzt, und die Empfehlungslogik las deshalb den ganzen
 * Katalog.
 *
 * Die Gerätewahl zeigt sofort, was sie bringt: neben jedem Haken steht, wie
 * viele Übungen dazukommen. Eine Liste mit dreißig Kästchen ohne Wirkung
 * füllt niemand aus.
 */

const ERFAHRUNG: [string, string, string][] = [
  ['einsteiger', 'Einsteiger', 'Unter einem Jahr regelmäßig. Weniger Volumen wirkt schon.'],
  ['fortgeschritten', 'Fortgeschritten', 'Ein bis drei Jahre. Der übliche Bereich.'],
  ['erfahren', 'Erfahren', 'Mehrere Jahre. Braucht mehr Reiz für dasselbe Ergebnis.'],
];

const ZIEL: [string, string, string][] = [
  ['hypertrophie', 'Muskelaufbau', '6 bis 12 Wiederholungen'],
  ['kraft', 'Maximalkraft', '3 bis 6 Wiederholungen, längere Pausen'],
  ['ausdauer', 'Kraftausdauer', '12 bis 20 Wiederholungen'],
  ['erhaltung', 'Erhalten', 'Weniger Volumen, Substanz halten'],
];

export default function ProfilPage() {
  const [profil, setProfil] = useState<Profil | null>(null);
  const [geraete, setGeraete] = useState<Geraet[]>([]);
  const [vorlagen, setVorlagen] = useState<Vorlage[]>([]);
  const [luecken, setLuecken] = useState<Ausruestungsluecke[]>([]);
  const [gespeichert, setGespeichert] = useState(false);

  useEffect(() => {
    api.get<Profil>('/profil').then(setProfil).catch(() => {});
    api.get<Geraet[]>('/profil/geraete').then(setGeraete).catch(() => {});
    api.get<Vorlage[]>('/profil/vorlagen').then(setVorlagen).catch(() => {});
  }, []);

  useEffect(() => {
    if (!profil) return;
    api.get<Ausruestungsluecke[]>('/profil/luecken').then(setLuecken).catch(() => {});
  }, [profil?.geraete.join(',')]);

  /** Wie viele Übungen ein noch fehlendes Gerät freischalten würde. */
  const gewinnJeGeraet = useMemo(() => {
    const zaehler: Record<string, number> = {};
    for (const l of luecken) {
      // Nur Lücken mit genau einer fehlenden Sache: bei zweien bringt das
      // einzelne Gerät die Übung noch nicht.
      if (l.fehlt.length === 1) {
        zaehler[l.fehlt[0]] = (zaehler[l.fehlt[0]] ?? 0) + 1;
      }
    }
    return zaehler;
  }, [luecken]);

  async function speichern(aenderung: Partial<Profil>) {
    const neu = await api.put<Profil>('/profil', aenderung);
    setProfil(neu);
    setGespeichert(true);
    setTimeout(() => setGespeichert(false), 1600);
  }

  async function vorlageWaehlen(id: string) {
    const neu = await api.post<Profil>(`/profil/vorlage/${id}`);
    setProfil(neu);
  }

  function geraetUmschalten(id: string) {
    if (!profil) return;
    const vorhanden = profil.geraete.includes(id);
    const neu = vorhanden
      ? profil.geraete.filter((g) => g !== id)
      : [...profil.geraete, id];
    speichern({ geraete: neu });
  }

  if (!profil) return <div className="page"><div className="skeleton" style={{ height: 200 }} /></div>;

  return (
    <div className="page fade-in">
      <div className="seiten-kopf">
        <h1>Ich</h1>
        {gespeichert && <span className="etikett gruen">gespeichert</span>}
      </div>

      {!profil.eingerichtet && (
        <div className="karte hinweis">
          <strong>Kurz einrichten</strong>
          <p className="klein">
            Solange hier nichts steht, schlägt die App auch Übungen mit Geräten
            vor, die du nicht hast. Eine Vorlage antippen reicht für den Anfang.
          </p>
        </div>
      )}

      <h2>Ausrüstung</h2>
      <div className="vorlagen">
        {vorlagen.map((v) => (
          <button key={v.id} className="vorlage" onClick={() => vorlageWaehlen(v.id)}>
            <strong>{v.name}</strong>
            <span className="klein gedaempft">{v.beschreibung}</span>
          </button>
        ))}
      </div>

      <div className="geraeteliste">
        {geraete.map((g) => {
          const hat = profil.geraete.includes(g.id);
          const gewinn = gewinnJeGeraet[g.id] ?? 0;
          return (
            <label key={g.id} className={`geraet ${hat ? 'hat' : ''}`}>
              <input type="checkbox" checked={hat} onChange={() => geraetUmschalten(g.id)} />
              <span className="geraet-name">{g.name}</span>
              {!hat && gewinn > 0 && (
                <span className="geraet-gewinn">+{gewinn} Übungen</span>
              )}
              {!hat && gewinn === 0 && g.ersatz_namen.length > 0 && (
                <span className="klein gedaempft">Ersatz: {g.ersatz_namen[0]}</span>
              )}
            </label>
          );
        })}
      </div>
      <p className="klein gedaempft">
        Boden, Wand, Stuhl und Türrahmen sind immer gesetzt und stehen deshalb
        nicht in der Liste.
      </p>

      <h2>Ziel</h2>
      <div className="wahlgruppe">
        {ZIEL.map(([wert, name, text]) => (
          <button
            key={wert}
            className={`wahl ${profil.ziel === wert ? 'aktiv' : ''}`}
            onClick={() => speichern({ ziel: wert })}
          >
            <strong>{name}</strong>
            <span className="klein gedaempft">{text}</span>
          </button>
        ))}
      </div>

      <h2>Erfahrung</h2>
      <div className="wahlgruppe">
        {ERFAHRUNG.map(([wert, name, text]) => (
          <button
            key={wert}
            className={`wahl ${profil.erfahrung === wert ? 'aktiv' : ''}`}
            onClick={() => speichern({ erfahrung: wert })}
          >
            <strong>{name}</strong>
            <span className="klein gedaempft">{text}</span>
          </button>
        ))}
      </div>

      <h2>Zahlen zu dir</h2>
      <div className="feldgruppe">
        <Feld
          beschriftung="Körpergewicht (kg)"
          wert={profil.koerpergewicht_kg}
          hinweis="Ohne diesen Wert hat jede Körpergewichtsübung ein Volumen von null."
          onSpeichern={(v) => speichern({ koerpergewicht_kg: v })}
        />
        <Feld
          beschriftung="Kleinster Gewichtssprung (kg)"
          wert={profil.gewichtsschritt_kg}
          hinweis="Was deine Hanteln hergeben. Vorschläge werden darauf gerundet."
          onSpeichern={(v) => speichern({ gewichtsschritt_kg: v })}
        />
        <Feld
          beschriftung="Schwerste Kurzhantel (kg)"
          wert={profil.kurzhantel_max_kg}
          hinweis="Ab hier schlägt die App eine schwerere Variante statt mehr Gewicht vor."
          onSpeichern={(v) => speichern({ kurzhantel_max_kg: v })}
        />
        <Feld
          beschriftung="Trainingstage pro Woche"
          wert={profil.trainingstage_pro_woche}
          onSpeichern={(v) => speichern({ trainingstage_pro_woche: Math.round(v) })}
        />
      </div>

      <h2>Weiter</h2>
      <div className="verweise">
        <Link className="verweis" to="/plans">Trainingspläne</Link>
        <Link className="verweis" to="/exercises">Übungskatalog</Link>
        <Link className="verweis" to="/body">Körperdaten und Ernährung</Link>
      </div>

      {luecken.length > 0 && (
        <>
          <h2>Was dir fehlt</h2>
          <p className="klein gedaempft">
            {luecken.length} Übungen im Katalog brauchen Geräte, die nicht
            eingetragen sind. {luecken.filter((l) => l.mit_ersatz).length} davon
            gehen mit etwas, das du hast.
          </p>
          {luecken.filter((l) => l.mit_ersatz).slice(0, 8).map((l) => (
            <div key={l.exercise_id} className="karte flach">
              <div>
                <strong>{l.name}</strong>
                <div className="klein gedaempft">
                  braucht {l.fehlt_namen.join(', ')} , geht mit {l.ersatz_namen.join(', ')}
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function Feld({ beschriftung, wert, hinweis, onSpeichern }: {
  beschriftung: string;
  wert: number | null;
  hinweis?: string;
  onSpeichern: (wert: number) => void;
}) {
  const [text, setText] = useState(wert != null ? String(wert) : '');
  useEffect(() => { setText(wert != null ? String(wert) : ''); }, [wert]);
  return (
    <div className="feld">
      <label>{beschriftung}</label>
      <input
        type="number"
        inputMode="decimal"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          const zahl = parseFloat(text.replace(',', '.'));
          if (!Number.isNaN(zahl) && zahl !== wert) onSpeichern(zahl);
        }}
      />
      {hinweis && <span className="klein gedaempft">{hinweis}</span>}
    </div>
  );
}
