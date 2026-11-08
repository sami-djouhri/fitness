import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import BottomNav from './components/BottomNav';
import { abgelehnt, abgelehntLeeren, beobachten, nachtragenStarten } from './warteschlange';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardPage from './pages/DashboardPage';
import WorkoutPage from './pages/WorkoutPage';
import PlanPage from './pages/PlanPage';
import ExercisesPage from './pages/ExercisesPage';
import ExerciseDetailPage from './pages/ExerciseDetailPage';
import BodyPage from './pages/BodyPage';
import KoerperPage from './pages/KoerperPage';
import ZahlenPage from './pages/ZahlenPage';
import ProfilPage from './pages/ProfilPage';

/**
 * Zustandsleiste oben. Sagt nicht mehr nur "offline", sondern was mit den
 * Eingaben passiert: ohne diese Rueckmeldung sah ein Netzausfall im Gym so
 * aus, als waere der Satz erfasst.
 */
function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);
  const [wartend, setWartend] = useState(0);

  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);

  // Die Beobachter melden jede Aenderung der Schlange, also auch das
  // Ablegen eines abgelehnten Auftrags. Deshalb hier mitlesen.
  const [abgelehntListe, setAbgelehntListe] = useState(abgelehnt);
  const [details, setDetails] = useState(false);
  useEffect(() => beobachten(n => { setWartend(n); setAbgelehntListe(abgelehnt()); }), []);

  if (abgelehntListe.length > 0) {
    const n = abgelehntListe.length;
    return (
      <div style={{
        position: 'fixed', top: 'var(--kopf-hoehe)', left: 0, right: 0, zIndex: 140,
        background: 'var(--danger)', color: 'var(--auf-primary)',
        padding: '6px 12px', fontSize: '0.8rem', fontWeight: 600, textAlign: 'center',
      }}>
        {n === 1 ? 'Ein Eintrag wurde' : `${n} Einträge wurden`} beim Nachtragen nicht übernommen.{' '}
        <button type="button" onClick={() => setDetails(d => !d)}
          style={{ textDecoration: 'underline', fontWeight: 600 }}>
          {details ? 'Weniger' : 'Was?'}
        </button>{' '}
        <button type="button" onClick={() => { abgelehntLeeren(); setDetails(false); }}
          style={{ textDecoration: 'underline', fontWeight: 600 }}>
          Ausblenden
        </button>
        {details && (
          <ul style={{ textAlign: 'left', fontWeight: 400, marginTop: 6, maxHeight: '40vh', overflowY: 'auto' }}>
            {abgelehntListe.map(a => (
              <li key={a.id} style={{ marginBottom: 4 }}>
                {new Date(a.am).toLocaleString('de')}: {a.method} {a.path} ({a.status})
                {a.body != null && <> mit {JSON.stringify(a.body)}</>}
                {a.meldung && <>, Antwort {a.meldung}</>}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (!offline && wartend === 0) return null;

  const text = offline
    ? wartend > 0
      ? `Kein Netz. ${wartend} ${wartend === 1 ? 'Eintrag wird' : 'Eintr\u00e4ge werden'} nachgetragen.`
      : 'Kein Netz. Eingaben werden gespeichert und sp\u00e4ter nachgetragen.'
    : `${wartend} ${wartend === 1 ? 'Eintrag wird' : 'Eintr\u00e4ge werden'} nachgetragen.`;

  return (
    <div style={{
      // Unter dem Kopf, nicht darueber: sonst deckt die Meldung den App-Namen.
      position: 'fixed', top: 'var(--kopf-hoehe)', left: 0, right: 0, zIndex: 140,
      background: offline ? 'var(--warning)' : 'var(--primary)',
      color: 'var(--auf-primary)', textAlign: 'center',
      padding: '6px 12px', fontSize: '0.8rem', fontWeight: 600,
    }}>
      {text}
    </div>
  );
}

export default function App() {
  // Wartende Eintraege nachtragen: beim Start und bei jeder Rueckkehr des Netzes.
  useEffect(() => { nachtragenStarten(); }, []);

  return (
    <ErrorBoundary>
      <saganta-kopf app="fitness"></saganta-kopf>
      <OfflineBanner />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/workout" element={<WorkoutPage />} />
        <Route path="/workout/:id" element={<WorkoutPage />} />
        <Route path="/koerper" element={<KoerperPage />} />
        <Route path="/zahlen" element={<ZahlenPage />} />
        <Route path="/profil" element={<ProfilPage />} />
        <Route path="/plans" element={<PlanPage />} />
        <Route path="/exercises" element={<ExercisesPage />} />
        <Route path="/exercises/:id" element={<ExerciseDetailPage />} />
        <Route path="/body" element={<BodyPage />} />
        {/* Alte Adressen bleiben erreichbar: Lesezeichen und der
            Startbildschirm des Handys zeigen noch dorthin. */}
        <Route path="/progress" element={<ZahlenPage />} />
      </Routes>
      <BottomNav />
    </ErrorBoundary>
  );
}
