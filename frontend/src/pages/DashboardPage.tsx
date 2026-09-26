import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type {
  DashboardSummary, Einheitsvorschlag, Exercise, Gruppenfrische, Gruppenwoche,
  PersonalRecord, Plan, Profil,
} from '../types';

/**
 * Heute: eine Frage, eine Antwort, ein Knopf.
 *
 * Die alte Startseite zeigte Begrüßung, Streak, Körperkarte, Empfehlungen und
 * Rekorde untereinander, und der Startknopf führte in ein leeres freies
 * Training. Was fehlte, war die Antwort auf die einzige Frage, die man beim
 * Öffnen hat: was mache ich jetzt, und womit fange ich an.
 *
 * ★ Der Knopf startet genau das, was darüber steht. Vorher zeigte die Seite
 * drei empfohlene Übungen mit Zielgewicht und startete etwas anderes.
 */

const DAUERN = [20, 30, 45, 60];

export default function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [einheit, setEinheit] = useState<Einheitsvorschlag | null>(null);
  const [dauer, setDauer] = useState(45);
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
    api.get<Einheitsvorschlag>(`/analyse/einheit?minuten=${dauer}`)
      .then(setEinheit).catch(() => {});
  }, [dauer]);

  // Den Plantag samt Übungen laden, damit unter dem Namen steht, was kommt.
  useEffect(() => {
    if (!summary?.next_plan_day_id) return;
    api.get<{ id: number }[]>('/plans')
      .then(async (liste) => {
        for (const p of liste) {
          const voll = await api.get<Plan>(`/plans/${p.id}`);
          if (voll.days.some((d) => d.id === summary.next_plan_day_id)) {
            setPlan(voll);
            return;
          }
        }
      })
      .catch(() => {});
  }, [summary?.next_plan_day_id]);

  const plantag = useMemo(
    () => plan?.days.find((d) => d.id === summary?.next_plan_day_id) ?? null,
    [plan, summary?.next_plan_day_id],
  );

  /**
   * ★★ Prüfen, ob der Plan mit der eingetragenen Ausrüstung überhaupt geht.
   *
   * Aufgefallen bei der ersten visuellen Prüfung: das Dashboard zeigte den
   * Tag "Pull A" mit Kreuzheben, Kabelrudern und Face Pulls auf einem Konto
   * mit Kurzhanteln und einer Klimmzugstange. Der Plan stammt aus einer Zeit
   * vor dem Ausrüstungsprofil, und niemand vergleicht beides von selbst. Der
   * Startknopf hätte in eine Sitzung geführt, in der vier von fünf Übungen
   * nicht ausführbar sind.
   */
  const [nichtMachbar, setNichtMachbar] = useState<string[]>([]);
  useEffect(() => {
    if (!plantag || plantag.exercises.length === 0) { setNichtMachbar([]); return; }
    api.get<Exercise[]>('/exercises?limit=400')
      .then((alle) => {
        const nachId = new Map(alle.map((e) => [e.id, e]));
        setNichtMachbar(
          plantag.exercises
            .filter((pe) => nachId.get(pe.exercise_id)?.machbar === false)
            .map((pe) => pe.exercise_name),
        );
      })
      .catch(() => setNichtMachbar([]));
  }, [plantag?.id, plantag?.exercises.length]);

  async function planTagStarten() {
    if (!summary?.next_plan_day_id || startet) return;
    setStartet(true);
    navigate('/workout', { state: { pendingPlanDayId: summary.next_plan_day_id } });
  }

  async function einheitStarten() {
    if (!einheit || einheit.uebungen.length === 0 || startet) return;
    setStartet(true);
    navigate('/workout', {
      state: {
        pendingName: `${einheit.gruppen.slice(0, 2).join(' und ')} , ${dauer} min`,
        pendingExerciseIds: einheit.uebungen.map((u) => u.exercise_id),
      },
    });
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

      {/* --- Der Plan, falls einer aktiv ist --- */}
      {plantag && (
        <div className="heute-karte">
          <div className="heute-oberzeile">
            {summary?.vorschlag_optional ? 'Nach Plan dran' : 'Heute dran'}
          </div>
          <div className="heute-titel">{plantag.name}</div>
          {summary?.tagestyp_hinweis && (
            <div className="begruendung">{summary.tagestyp_hinweis}</div>
          )}
          <div className="heute-uebungen">
            {plantag.exercises.map((pe) => (
              <div key={pe.id} className="heute-uebung">
                <span>{pe.exercise_name}</span>
                <span className="ziel">
                  {pe.target_sets} x {pe.target_reps_min}
                  {pe.target_reps_max !== pe.target_reps_min && `-${pe.target_reps_max}`}
                </span>
              </div>
            ))}
            {plantag.exercises.length === 0 && (
              <div className="klein gedaempft">
                Dieser Tag hat noch keine Übungen.{' '}
                <Link to="/plans">Jetzt eintragen</Link>
              </div>
            )}
          </div>
          {nichtMachbar.length > 0 && (
            <div className="planwarnung">
              <strong>
                {nichtMachbar.length} von {plantag.exercises.length} Übungen
                brauchen Geräte, die nicht eingetragen sind
              </strong>
              <div className="klein">{nichtMachbar.join(' , ')}</div>
              <div className="klein" style={{ marginTop: 6 }}>
                <Link to="/plans">Plan anpassen</Link>
                {' oder '}
                <Link to="/plans">eine Vorlage nehmen</Link>
                {', die aus deiner Ausrüstung entsteht.'}
              </div>
            </div>
          )}
          <button className="btn-primary" style={{ width: '100%' }}
                  onClick={planTagStarten} disabled={startet}>
            {plantag.name} starten
          </button>
        </div>
      )}

      {/* --- Ohne Plan: eine Einheit nach Bedarf --- */}
      {!plantag && einheit && (
        <div className="heute-karte">
          <div className="heute-oberzeile">Vorschlag für heute</div>
          <div className="heute-titel">
            {einheit.gruppen.length > 0 ? einheit.gruppen.join(' , ') : 'Freies Training'}
          </div>
          <div className="dauerwahl">
            {DAUERN.map((d) => (
              <button key={d} className={dauer === d ? 'aktiv' : ''}
                      onClick={() => setDauer(d)}>
                {d} min
              </button>
            ))}
          </div>
          <div className="heute-uebungen">
            {einheit.uebungen.map((u) => (
              <div key={u.exercise_id} className="heute-uebung">
                <span>{u.name}</span>
                <span className="ziel">
                  {u.saetze} x {u.wdh ?? '?'}
                  {u.gewicht_kg != null && ` , ${u.gewicht_kg} kg`}
                </span>
              </div>
            ))}
          </div>
          {einheit.uebungen.length > 0 ? (
            <button className="btn-primary" style={{ width: '100%' }}
                    onClick={einheitStarten} disabled={startet}>
              Starten ({einheit.geplante_minuten} min)
            </button>
          ) : (
            <div className="klein gedaempft">
              Kein Vorschlag möglich. Prüfe unter <Link to="/profil">Ich</Link>,
              ob deine Ausrüstung eingetragen ist.
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
                {baustellen.map((g) => `${g.name} (${g.direkt.toFixed(0)} von ${g.mev})`).join(' , ')}
              </div>
            </div>
          )}
          {belastet.length > 0 && (
            <div>
              <strong className="klein">Noch belastet</strong>
              <div className="klein gedaempft">
                {belastet.map((f) =>
                  `${f.name} (wieder bereit in ${Math.round(f.bereit_in_stunden)} h)`).join(' , ')}
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
