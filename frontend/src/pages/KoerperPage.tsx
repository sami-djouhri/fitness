import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { Faerbung } from '../components/Koerpermodell';
import type {
  Exercise, Registry, Muskelgruppe, Muskel, Muskelstand, Gruppenfrische,
} from '../types';

/**
 * ★ Nachgeladen statt mitgeliefert: three.js wiegt rund 470 kB und wird nur
 * auf dieser Seite gebraucht. Im Hauptbündel hätte jeder Start der App es
 * mitgezogen, auch wenn jemand nur einen Satz einträgt. Gemessen wuchs das
 * Bündel dadurch von 712 kB auf 1,19 MB.
 */
const Koerpermodell = lazy(() => import('../components/Koerpermodell'));

/**
 * Der Körper als Einstieg: anfassen, auswählen, sehen was drankommt.
 *
 * Ersetzt die alte Kombination aus Dashboard-Karte und Übungsliste. Drei
 * Dinge, die vorher nicht gingen und ausdrücklich gewünscht waren:
 *
 * 1. Drehen und Zoomen statt zwei fester Ansichten.
 * 2. Einzelne Muskeln statt zehn Regionen. Wer den Vastus medialis antippt,
 *    bekommt eine andere Liste als beim Rectus femoris.
 * 3. ★ Die Abdeckungsansicht: beim Ab- und Anwählen von Übungen färbt sich
 *    das Modell sofort um. Man sieht, ob eine Auswahl mehr oder weniger
 *    Partien trifft, statt es sich aus einer Liste denken zu müssen.
 */

type Ebene = 'gruppe' | 'muskel';

export default function KoerperPage() {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [stand, setStand] = useState<Record<string, Muskelstand>>({});
  const [frische, setFrische] = useState<Gruppenfrische[]>([]);
  const [gewaehlterMuskel, setGewaehlterMuskel] = useState<string | null>(null);
  const [gewaehlteGruppe, setGewaehlteGruppe] = useState<string | null>(null);
  const [uebungen, setUebungen] = useState<Exercise[]>([]);
  const [laedt, setLaedt] = useState(false);
  const [faerbung, setFaerbung] = useState<Faerbung>('frische');
  const [nurMachbar, setNurMachbar] = useState(true);
  const [artFilter, setArtFilter] = useState<'training' | 'dehnung'>('training');
  const [vorschau, setVorschau] = useState<Exercise | null>(null);
  /** Für die Abdeckungsansicht: welche Übungen der Liste sind an. */
  const [ausgeschlossen, setAusgeschlossen] = useState<Set<number>>(new Set());
  const [alleZeigen, setAlleZeigen] = useState(false);

  useEffect(() => {
    api.get<Registry>('/analyse/registry').then(setRegistry).catch(() => {});
    api.get<Record<string, Muskelstand>>('/analyse/muskeln').then(setStand).catch(() => {});
    api.get<Gruppenfrische[]>('/analyse/frische').then(setFrische).catch(() => {});
  }, []);

  const muskelIndex = useMemo(() => {
    const m = new Map<string, Muskel>();
    registry?.muskeln.forEach((x) => m.set(x.id, x));
    return m;
  }, [registry]);

  const gruppenIndex = useMemo(() => {
    const m = new Map<string, Muskelgruppe>();
    registry?.gruppen.forEach((x) => m.set(x.id, x));
    return m;
  }, [registry]);

  const frischeIndex = useMemo(() => {
    const m = new Map<string, Gruppenfrische>();
    frische.forEach((f) => m.set(f.gruppe, f));
    return m;
  }, [frische]);

  /* ---------------------------------------------------------------- */
  /*  Was das Modell einfärbt                                          */
  /* ---------------------------------------------------------------- */

  const werte = useMemo(() => {
    const ergebnis: Record<string, number> = {};

    if (faerbung === 'abdeckung') {
      // Der höchste Anteil, den irgendeine noch angewählte Übung der Liste
      // auf diesen Muskel bringt.
      for (const ex of uebungen) {
        if (ausgeschlossen.has(ex.id)) continue;
        for (const [mid, anteil] of Object.entries(ex.muskel_anteile ?? {})) {
          if (!ergebnis[mid] || anteil > ergebnis[mid]) ergebnis[mid] = anteil;
        }
      }
      return ergebnis;
    }

    // Frische: pro Muskel aus der Gruppenfrische, damit Modell und
    // Erholungsanzeige dieselbe Zahl benutzen.
    for (const muskel of muskelIndex.values()) {
      const f = frischeIndex.get(muskel.gruppe);
      ergebnis[muskel.id] = f ? f.frische : 1;
    }
    return ergebnis;
  }, [faerbung, uebungen, ausgeschlossen, muskelIndex, frischeIndex]);

  /** In der Abdeckungsansicht die Muskeln der gewählten Übung hervorheben. */
  const hervorgehoben = useMemo(() => {
    if (!vorschau) return [];
    return Object.entries(vorschau.muskel_anteile ?? {})
      .filter(([, anteil]) => anteil >= 0.6)
      .map(([mid]) => mid);
  }, [vorschau]);

  /* ---------------------------------------------------------------- */
  /*  Auswahl                                                          */
  /* ---------------------------------------------------------------- */

  async function ladeUebungen(schluessel: string, ebene: Ebene) {
    setLaedt(true);
    setAusgeschlossen(new Set());
    setVorschau(null);
    setAlleZeigen(false);
    const p = new URLSearchParams();
    p.set(ebene === 'muskel' ? 'muscle' : 'gruppe', schluessel);
    p.set('limit', '60');
    if (nurMachbar) p.set('nur_machbar', 'true');
    if (artFilter === 'dehnung') p.set('category', 'Dehnung');
    try {
      setUebungen(await api.get<Exercise[]>(`/exercises?${p}`));
    } finally {
      setLaedt(false);
    }
  }

  function beiMuskelKlick(muskelId: string) {
    const muskel = muskelIndex.get(muskelId);
    if (!muskel) return;
    if (gewaehlterMuskel === muskelId) {
      // Zweiter Tipp auf denselben Muskel: eine Ebene hoch zur Gruppe.
      setGewaehlterMuskel(null);
      setGewaehlteGruppe(muskel.gruppe);
      ladeUebungen(muskel.gruppe, 'gruppe');
      return;
    }
    setGewaehlterMuskel(muskelId);
    setGewaehlteGruppe(muskel.gruppe);
    ladeUebungen(muskelId, 'muskel');
  }

  function gruppeWaehlen(gruppeId: string) {
    setGewaehlterMuskel(null);
    setGewaehlteGruppe(gruppeId);
    ladeUebungen(gruppeId, 'gruppe');
  }

  useEffect(() => {
    if (!gewaehlteGruppe && !gewaehlterMuskel) return;
    ladeUebungen(gewaehlterMuskel ?? gewaehlteGruppe!,
                 gewaehlterMuskel ? 'muskel' : 'gruppe');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nurMachbar, artFilter]);

  function umschalten(ex: Exercise) {
    setAusgeschlossen((vorher) => {
      const neu = new Set(vorher);
      if (neu.has(ex.id)) neu.delete(ex.id);
      else neu.add(ex.id);
      return neu;
    });
    // Beim Abwählen lohnt der Blick aufs Modell: also automatisch dorthin
    // umschalten, statt zu erwarten, dass jemand den Knopf findet.
    setFaerbung('abdeckung');
  }

  /** Anteil einer Übung auf die gerade gewählte Stelle. */
  function anteilVon(ex: Exercise): number {
    if (gewaehlterMuskel) return ex.muskel_anteile?.[gewaehlterMuskel] ?? 0;
    const werte = Object.entries(ex.muskel_anteile ?? {})
      .filter(([mid]) => muskelIndex.get(mid)?.gruppe === gewaehlteGruppe)
      .map(([, a]) => a);
    return werte.length ? Math.max(...werte) : 0;
  }

  /**
   * ★ Standardmäßig nur, was die Stelle wirklich trifft. Beim Antippen von
   * "Trizeps" kamen 26 Übungen, darunter Liegestütze an der Wand mit einem
   * Anteil von 0,4. Eine Liste, die alles enthält, beantwortet die Frage
   * nicht mehr, mit der man sie geöffnet hat.
   */
  const sichtbar = useMemo(() => {
    if (alleZeigen) return uebungen;
    const stark = uebungen.filter((e) => anteilVon(e) >= 0.6);
    return stark.length >= 3 ? stark : uebungen.slice(0, 8);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uebungen, alleZeigen, gewaehlterMuskel, gewaehlteGruppe, muskelIndex]);

  const aktiv = sichtbar.filter((e) => !ausgeschlossen.has(e.id));
  const getroffeneGruppen = useMemo(() => {
    const ids = new Set<string>();
    for (const ex of aktiv) {
      for (const [mid, anteil] of Object.entries(ex.muskel_anteile ?? {})) {
        if (anteil >= 0.6) {
          const m = muskelIndex.get(mid);
          if (m) ids.add(m.gruppe);
        }
      }
    }
    return ids;
  }, [aktiv, muskelIndex]);

  const gewaehlt = gewaehlterMuskel
    ? muskelIndex.get(gewaehlterMuskel)
    : null;
  const gruppe = gewaehlteGruppe ? gruppenIndex.get(gewaehlteGruppe) : null;
  const gruppenFrische = gewaehlteGruppe ? frischeIndex.get(gewaehlteGruppe) : null;

  const fusszeile = gewaehlt
    ? `${gewaehlt.name} (${gewaehlt.fachname})`
    : gruppe
      ? gruppe.name
      : 'Tippe einen Muskel an';

  return (
    <div className="page fade-in">
      <div className="seiten-kopf">
        <h1>Körper</h1>
        <div className="segment">
          <button
            className={faerbung === 'frische' ? 'aktiv' : ''}
            onClick={() => setFaerbung('frische')}
          >
            Erholung
          </button>
          <button
            className={faerbung === 'abdeckung' ? 'aktiv' : ''}
            onClick={() => setFaerbung('abdeckung')}
            disabled={uebungen.length === 0}
          >
            Abdeckung
          </button>
        </div>
      </div>

      <Suspense fallback={
        <div className="koerpermodell">
          <div className="skeleton" style={{ height: 420 }} />
        </div>
      }>
        <Koerpermodell
          werte={werte}
          faerbung={faerbung}
          ausgewaehlt={gewaehlterMuskel}
          hervorgehoben={hervorgehoben}
          onMuskelKlick={beiMuskelKlick}
          muster={vorschau?.muster ?? null}
          fusszeile={fusszeile}
        />
      </Suspense>

      <Legende faerbung={faerbung} />

      {/* Gruppen als Liste, für alle, die lieber tippen als drehen. */}
      {registry && (
        <div className="gruppen-chips">
          {registry.gruppen.map((g) => {
            const f = frischeIndex.get(g.id);
            return (
              <button
                key={g.id}
                className={`gruppen-chip ${gewaehlteGruppe === g.id ? 'aktiv' : ''}`}
                onClick={() => gruppeWaehlen(g.id)}
                title={f?.stunden_seit != null
                  ? `Zuletzt vor ${Math.round(f.stunden_seit)} Stunden`
                  : 'Noch nicht trainiert'}
              >
                <span
                  className="gruppen-chip-punkt"
                  style={{ background: farbeFrische(f?.frische ?? 1) }}
                />
                {g.name}
              </button>
            );
          })}
        </div>
      )}

      {gewaehlteGruppe && gruppe && (
        <div className="karte">
          <div className="karte-kopf">
            <div>
              <strong>{gewaehlt ? gewaehlt.name : gruppe.name}</strong>
              {gewaehlt && (
                <div className="klein gedaempft">
                  {gewaehlt.fachname}
                  {gewaehlt.funktion && <> &middot; {gewaehlt.funktion}</>}
                </div>
              )}
              {!gewaehlt && gruppenFrische && (
                <div className="klein gedaempft">
                  {gruppenFrische.stunden_seit == null
                    ? 'Noch nicht trainiert'
                    : `Zuletzt vor ${Math.round(gruppenFrische.stunden_seit)} h`}
                  {gruppenFrische.bereit_in_stunden > 0 && (
                    <> &middot; wieder bereit in {Math.round(gruppenFrische.bereit_in_stunden)} h</>
                  )}
                </div>
              )}
            </div>
            {gewaehlt && (
              <button className="knopf-flach" onClick={() => gruppeWaehlen(gruppe.id)}>
                ganze Gruppe
              </button>
            )}
          </div>

          {/* Volumen-Korridor der Gruppe */}
          <Korridor gruppe={gruppe} />

          <div className="filterzeile">
            <div className="segment klein">
              <button
                className={artFilter === 'training' ? 'aktiv' : ''}
                onClick={() => setArtFilter('training')}
              >
                Training
              </button>
              <button
                className={artFilter === 'dehnung' ? 'aktiv' : ''}
                onClick={() => setArtFilter('dehnung')}
              >
                Dehnung
              </button>
            </div>
            <label className="schalter">
              <input
                type="checkbox"
                checked={nurMachbar}
                onChange={(e) => setNurMachbar(e.target.checked)}
              />
              nur was ich habe
            </label>
          </div>

          {laedt && <div className="gedaempft klein">Laden...</div>}
          {!laedt && sichtbar.length === 0 && (
            <div className="leer">
              Keine Übung für diese Auswahl.
              {nurMachbar && ' Ohne den Ausrüstungsfilter gibt es womöglich mehr.'}
            </div>
          )}

          {sichtbar.length > 0 && (
            <div className="abdeckung-hinweis">
              {aktiv.length} von {sichtbar.length} Übungen angewählt, sie treffen{' '}
              {getroffeneGruppen.size} Muskelgruppe{getroffeneGruppen.size === 1 ? '' : 'n'}.
              {ausgeschlossen.size > 0 && (
                <button className="knopf-flach" onClick={() => setAusgeschlossen(new Set())}>
                  alle zurück
                </button>
              )}
              {uebungen.length > sichtbar.length && (
                <button className="knopf-flach" onClick={() => setAlleZeigen(true)}>
                  auch die {uebungen.length - sichtbar.length}, die nur mitarbeiten
                </button>
              )}
              {alleZeigen && uebungen.length > 8 && (
                <button className="knopf-flach" onClick={() => setAlleZeigen(false)}>
                  nur die wichtigsten
                </button>
              )}
            </div>
          )}

          <ul className="uebungsliste">
            {sichtbar.map((ex) => {
              const aus = ausgeschlossen.has(ex.id);
              const anteil = anteilVon(ex);
              return (
                <li
                  key={ex.id}
                  className={`uebungszeile ${aus ? 'aus' : ''}`}
                  onMouseEnter={() => setVorschau(ex)}
                  onMouseLeave={() => setVorschau(null)}
                >
                  <button
                    className="zeilen-haken"
                    onClick={() => umschalten(ex)}
                    aria-label={aus ? 'Übung einbeziehen' : 'Übung ausblenden'}
                  >
                    {aus ? '☐' : '☑'}
                  </button>
                  <button
                    className="zeilen-titel"
                    onClick={() => setVorschau(vorschau?.id === ex.id ? null : ex)}
                  >
                    <span>{ex.name}</span>
                    <span className="klein gedaempft">
                      {ex.equipment}
                      {ex.griff && <> &middot; {ex.griff}</>}
                      {ex.is_compound && <> &middot; Grundübung</>}
                      {!ex.machbar && (
                        <> &middot; <span className="warnung">
                          fehlt: {ex.fehlt_namen.join(', ')}
                        </span></>
                      )}
                    </span>
                  </button>
                  <div className="anteil-balken" title={`Anteil ${Math.round(anteil * 100)} %`}>
                    <div style={{ width: `${Math.round(anteil * 100)}%` }} />
                  </div>
                  <Link className="zeilen-pfeil" to={`/exercises/${ex.id}`}>›</Link>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */

function Korridor({ gruppe }: { gruppe: Muskelgruppe }) {
  const max = Math.max(gruppe.mrv, 1);
  const anteil = (n: number) => `${(n / max) * 100}%`;
  return (
    <div className="korridor">
      <div className="korridor-schiene">
        <div className="korridor-mav"
             style={{ left: anteil(gruppe.mav_min),
                      width: anteil(gruppe.mav_max - gruppe.mav_min) }} />
        <div className="korridor-marke" style={{ left: anteil(gruppe.mev) }} />
      </div>
      <div className="korridor-text">
        Wirksam ab {gruppe.mev} Sätzen pro Woche, am besten {gruppe.mav_min} bis{' '}
        {gruppe.mav_max}, mehr als {gruppe.mrv} bringt nichts mehr.
      </div>
    </div>
  );
}

function Legende({ faerbung }: { faerbung: Faerbung }) {
  const eintraege = faerbung === 'frische'
    ? [
        { farbe: '#ef4444', text: 'belastet' },
        { farbe: '#facc15', text: 'erholt sich' },
        { farbe: '#22c55e', text: 'bereit' },
      ]
    : [
        { farbe: '#39414f', text: 'kommt nicht dran' },
        { farbe: '#2b7fd4', text: 'arbeitet mit' },
        { farbe: '#5eb2ff', text: 'Hauptziel' },
      ];
  return (
    <div className="legende">
      {eintraege.map((e) => (
        <span key={e.text} className="legende-eintrag">
          <span className="legende-punkt" style={{ background: e.farbe }} />
          {e.text}
        </span>
      ))}
    </div>
  );
}

function farbeFrische(wert: number): string {
  if (wert >= 0.8) return '#22c55e';
  if (wert >= 0.6) return '#4ade80';
  if (wert >= 0.35) return '#facc15';
  return '#ef4444';
}
