import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import BottomNav from './components/BottomNav';
import { beobachten, nachtragenStarten } from './warteschlange';
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

  useEffect(() => beobachten(setWartend), []);

  if (!offline && wartend === 0) return null;

  const text = offline
    ? wartend > 0
      ? `Kein Netz. ${wartend} ${wartend === 1 ? 'Eintrag wird' : 'Eintr\u00e4ge werden'} nachgetragen.`
      : 'Kein Netz. Eingaben werden gespeichert und sp\u00e4ter nachgetragen.'
    : `${wartend} ${wartend === 1 ? 'Eintrag wird' : 'Eintr\u00e4ge werden'} nachgetragen.`;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
      background: offline ? 'var(--warning)' : 'var(--primary)',
      color: offline ? '#000' : '#fff', textAlign: 'center',
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
        <Route path="/achievements" element={<ZahlenPage />} />
      </Routes>
      <BottomNav />
    </ErrorBoundary>
  );
}
