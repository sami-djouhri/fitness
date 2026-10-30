import { NavLink } from 'react-router-dom';

/**
 * Fünf Punkte statt sechs.
 *
 * Raus ist "Erfolge": 18 Abzeichen, zwei davon freigeschaltet, und keine
 * Aussage über das Training. An der Stelle steht jetzt "Zahlen" mit dem
 * Wochenvolumen gegen die Bereiche, in denen ein Muskel wächst.
 *
 * "Übungen" ist kein eigener Punkt mehr, sondern liegt unter "Körper": man
 * sucht eine Übung fast immer für eine bestimmte Stelle, und die wählt man
 * am Modell. Über die Suche ist der Katalog weiter direkt erreichbar.
 */

const icons: Record<string, JSX.Element> = {
  heute: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  training: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6.5 6.5h11M6 12h12M2 9v6M6 7v10M18 7v10M22 9v6" />
    </svg>
  ),
  koerper: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="4.5" r="2.5" />
      <path d="M12 7v7M7.5 10.5h9M12 14l-3 7M12 14l3 7" />
    </svg>
  ),
  zahlen: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  ich: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
    </svg>
  ),
};

const punkte = [
  { to: '/', label: 'Heute', icon: 'heute' },
  { to: '/workout', label: 'Training', icon: 'training' },
  { to: '/koerper', label: 'Körper', icon: 'koerper' },
  { to: '/zahlen', label: 'Zahlen', icon: 'zahlen' },
  { to: '/profil', label: 'Ich', icon: 'ich' },
];

export default function BottomNav() {
  return (
    <nav className="unterleiste">
      {punkte.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `unterleiste-punkt ${isActive ? 'aktiv' : ''}`}
        >
          {icons[icon]}
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
