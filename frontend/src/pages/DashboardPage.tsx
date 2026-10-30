import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type {
  DashboardSummary, Gruppenfrische, Gruppenwoche, PersonalRecord,
  Profil, TrainingJetzt,
} from '../types';
import { startzustand, ziel } from '../trainingjetzt';

/**
 * Heute: eine Frage, eine Antwort, ein Knopf.
 *
 * Die alte Startseite zeigte Begrüßung, Streak, Körperkarte, Empfehlungen und
 * Rekorde untereinander, und der Startknopf führte in ein leeres freies
 * Training. Was fehlte, war die Antwort auf die einzige Frage, die man beim
 * Öffnen hat: was mache ich jetzt, und womit fange ich an.
 *
 * Der Knopf startet genau das, was darüber steht. Vorher zeigte die Seite
 * drei empfohlene Übungen mit Zielgewicht und startete etwas anderes.
 *
 * Die Antwort kommt seit dem 2026-10-24 aus ``/api/training/jetzt`` und
 * wird nicht mehr hier zusammengesetzt. Vorher baute diese Seite sie aus fünf
 * Abfragen selbst nach (``/progress/summary`` für den Plantag, ``/plans`` und
 * je ein ``/plans/{id}``, bis der passende Plan gefunden war, dazu alle
 * Übungen für die Ausrüstungsprüfung) und kam zu einem anderen Ergebnis als
 * der Dienst, der für genau diese Frage gebaut wurde: sie zeigte den ganzen
 * Plantag, auch die Übungen, deren Gerät gerade fehlt, und bot die Dauerwahl
 * nur an, wenn kein Plan aktiv war. Wer einen Plan hatte, konnte seine Zeit
 * also nicht angeben, und die Einheit wurde nie darauf zugeschnitten.
 */

const DAUERN = [20, 30, 45, 60];

export default function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [jetzt, setJetzt] = useState<TrainingJetzt | null>(null);
  /**
   * ``null`` heißt "noch nichts gewählt". Beim ersten Laden wird deshalb
   * **ohne** ``minuten`` gefragt, damit der Dienst den Kalender befragen kann.
   * Mit einer festen 45 als Anfangswert kam der Kalender nie zum Zug: jede
   * Anfrage trug eine Zahl, und eine genannte Zahl schlägt die Planung. Die
   * Zahl lag die ganze Zeit im Haus und wurde nie geholt.
   */
  const [dauer, setDauer] = useState<number | null>(null);
  const [woche, setWoche] = useState<Gruppenwoche[]>([]);
  const [frische, setFrische] = useState<Gruppenfrische[]>([]);
  const [prs, setPrs] = useState<PersonalRecord[]>([]);
  const [profil, setProfil] = useState<Profil | null>(null);
  const [startet, setStartet] = useState(false);

  useEffect(() => {
    api.get<DashboardSummary>('/progress/summary').then(setSummary).catch(() => {});
    api.get<Gruppenwoche[]>('/analyse/volumen').then(setWoche).catch(() => {});
    api.get<Gruppenfrische[]>('/analyse/frische').then(setFrische).catch(() => {});
    api.get<PersonalRecord[]>('/progress/prs/recent').then(setPrs).catch(() => {});
    api.get<Profil>('/profil').then(setProfil).catch(() => {});
  }, []);

  useEffect(() => {
    api.get<TrainingJetzt>(
      dauer === null ? '/training/jetzt' : `/training/jetzt?minuten=${dauer}`)
      .then(setJetzt).catch(() => {});
  }, [dauer]);

  // Welche Dauer angezeigt wird: die gewählte, sonst die, mit der geantwortet
  // wurde. Eine aus dem Kalender stammende Zahl ist selten eine der vier
  // runden, deshalb kommt sie als zusätzlicher Knopf dazu statt die Reihe zu
  // ersetzen (Entscheid: vorbelegen, Wahl bleibt).
  const aktiveDauer = dauer ?? jetzt?.minuten ?? null;
  const knoepfe = aktiveDauer !== null && !DAUERN.includes(aktiveDauer)
    ? [...DAUERN, aktiveDauer].sort((a, b) => a - b)
    : DAUERN;

  /** Starten heißt: genau diese Liste, mit diesen Sätzen (``trainingjetzt.ts``). */
  async function starten() {
    if (!jetzt || jetzt.uebungen.length === 0 || startet) return;
    setStartet(true);
    navigate('/workout', { state: startzustand(jetzt) });
  }

  const baustellen = woche
    .filter((g) => g.mev > 0 && (g.bewertung === 'unter_mv' || g.bewertung === 'erhaltung'))
    .slice(0, 3);
  const belastet = frische
    .filter((f) => f.frische < 0.5)
    .sort((a, b) => a.frische - b.frische)
    .slice(0, 3);

  return (
    <div className="page fade-in">
      <div className="seiten-kopf">
        <h1>{begruessung()}</h1>
        {summary && (
          <span className="klein gedaempft">
            {summary.current_streak > 0
              ? `${summary.current_streak} ${summary.current_streak === 1 ? 'Tag' : 'Tage'} in Folge`
              : `${summary.workouts_7d} diese Woche`}
          </span>
        )}
      </div>

      {profil && !profil.eingerichtet && (
        <Link to="/profil" className="karte hinweis" style={{ display: 'block' }}>
          <strong>Einmal einrichten</strong>
          <div className="klein">
            Ohne deine Ausrüstung schlägt die App auch Übungen mit Geräten vor,
            die du nicht hast. Zwei Tipps genügen.
          </div>
        </Link>
      )}

      {/* --- Die Einheit für jetzt --- */}
      {jetzt && (
        <div className="heute-karte">
          <div className="heute-oberzeile">
            {jetzt.quelle === 'plan'
              ? (summary?.vorschlag_optional ? 'Nach Plan dran' : 'Heute dran')
              : 'Vorschlag für heute'}
          </div>
          <div className="heute-titel">{jetzt.titel}</div>
          <div className="begruendung">{jetzt.begruendung}</div>

          {/* Die Zeit gilt für beide Wege, nicht nur ohne Plan. */}
          <div className="dauerwahl">
            {knoepfe.map((d) => (
              <button key={d} className={aktiveDauer === d ? 'aktiv' : ''}
                      onClick={() => setDauer(d)}>
                {d} min
              </button>
            ))}
          </div>
          {jetzt.minuten_quelle === 'kalender' && dauer === null && (
            <div className="klein gedaempft" style={{ marginTop: -6, marginBottom: 10 }}>
              Heute sind {jetzt.minuten} Minuten eingeplant. Tippe auf eine
              andere Dauer, wenn du mehr oder weniger Zeit hast.
            </div>
          )}

          <div className="heute-uebungen">
            {jetzt.uebungen.map((u) => (
              <div key={u.exercise_id} className="heute-uebung">
                <span>
                  <Link to={`/exercises/${u.exercise_id}`} style={{ color: 'inherit' }}>
                    {u.name}
                  </Link>
                  {u.ergaenzt && <span className="etikett" style={{ marginLeft: 6 }}>ergänzt</span>}
                </span>
                <span className="ziel">
                  {ziel(u)}
                  {u.gekuerzt_von != null && (
                    <span className="gedaempft"> (von {u.gekuerzt_von})</span>
                  )}
                </span>
              </div>
            ))}
            {jetzt.uebungen.length === 0 && (
              <div className="klein gedaempft">
                Kein Vorschlag möglich. Prüfe unter <Link to="/profil">Ich</Link>,
                ob deine Ausrüstung eingetragen ist.
              </div>
            )}
          </div>

          {/* Einmal unter der Liste statt in jeder Zeile: bei einem frischen
              Plan ist jede Übung geschätzt, und sieben gleiche Klammern
              verdecken die Liste, um die es geht. */}
          {jetzt.uebungen.some((u) => u.gewicht_quelle === 'geschaetzt') && (
            <div className="klein gedaempft" style={{ marginTop: -6, marginBottom: 10 }}>
              ~ ist geschätzt, aus Körpergewicht und Erfahrung. Was du im ersten
              Satz einträgst, ersetzt die Schätzung dauerhaft.
            </div>
          )}
          {jetzt.uebungen.some((u) => u.gewicht_quelle === 'fehlt') && (
            <div className="klein gedaempft" style={{ marginTop: -6, marginBottom: 10 }}>
              ? heißt: dort gehört ein Gewicht hin, es lässt sich aber keines
              schätzen. Trag im ersten Satz ein, was du geschafft hast.
            </div>
          )}

          {/* Zwei Töne, nicht einer. Owner-Beobachtung am Bild vom
              2026-10-24: der Kasten zog mehr Aufmerksamkeit als die
              Übungsliste darüber. Das lag nicht an seiner Größe, sondern
              daran, dass auch "Brust kam diese Woche zu kurz" die volle
              Warnbehandlung bekam. Eine Erklärung, die aussieht wie ein
              Alarm, macht den echten Alarm daneben unsichtbar.

              Was eine Handlung verlangt, steht im Warnkasten und bringt den
              Weg gleich mit: der Plan stammt oft aus der Zeit vor dem
              Ausrüstungsprofil, da reicht eine Feststellung nicht. */}
          {jetzt.warnungen.length > 0 && (
            <div className="planwarnung">
              {jetzt.warnungen.map((w, i) => (
                <div key={i} className="klein">{w}</div>
              ))}
              {jetzt.fehlende_ausruestung.length > 0 && (
                <div className="klein" style={{ marginTop: 6 }}>
                  <Link to="/plans">Plan anpassen</Link>
                  {' oder '}
                  <Link to="/profil">Ausrüstung nachtragen</Link>.
                </div>
              )}
            </div>
          )}

          {/* Was nur erklärt, erklärt auch leise. */}
          {jetzt.hinweise.length > 0 && (
            <div className="klein gedaempft" style={{ marginBottom: 10 }}>
              {jetzt.hinweise.map((h, i) => (
                <div key={i}>{h}</div>
              ))}
            </div>
          )}

          {jetzt.uebungen.length > 0 && (
            <button className="btn-primary" style={{ width: '100%' }}
                    onClick={starten} disabled={startet}>
              Starten ({jetzt.geplante_minuten} min)
            </button>
          )}

          {jetzt.minuten_quelle === 'vorgabe' && (
            <div className="klein gedaempft" style={{ marginTop: 6 }}>
              Gerechnet mit {jetzt.minuten} Minuten als Vorgabe.
            </div>
          )}
        </div>
      )}

      {/* --- Zustand in zwei Zeilen --- */}
      {(baustellen.length > 0 || belastet.length > 0) && (
        <div className="karte">
          {baustellen.length > 0 && (
            <div style={{ marginBottom: belastet.length ? 10 : 0 }}>
              <strong className="klein">Kommt zu kurz</strong>
              <div className="klein gedaempft">
                {baustellen.map((g) => `${g.name} (${g.direkt.toFixed(0)} von ${g.mev})`).join(', ')}
              </div>
            </div>
          )}
          {belastet.length > 0 && (
            <div>
              <strong className="klein">Noch belastet</strong>
              <div className="klein gedaempft">
                {belastet.map((f) =>
                  `${f.name} (wieder bereit in ${Math.round(f.bereit_in_stunden)} h)`).join(', ')}
              </div>
            </div>
          )}
          <Link className="knopf-flach" to="/zahlen" style={{ paddingLeft: 0 }}>
            alle Zahlen
          </Link>
        </div>
      )}

      {prs.length > 0 && (
        <>
          <h2>Zuletzt verbessert</h2>
          {prs.slice(0, 3).map((pr) => (
            <Link key={pr.id} to={`/exercises/${pr.exercise_id}`}
                  className="karte flach" style={{ color: 'inherit' }}>
              <div>
                <strong>{pr.exercise_name}</strong>
                <div className="klein gedaempft">
                  {pr.pr_type === 'max_reps'
                    ? `${pr.value} Wiederholungen`
                    : `${pr.value.toFixed(1)} kg`}
                </div>
              </div>
              <span className="etikett gruen">neu</span>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}

function begruessung(): string {
  const h = new Date().getHours();
  if (h < 11) return 'Guten Morgen';
  if (h < 18) return 'Guten Tag';
  return 'Guten Abend';
}
