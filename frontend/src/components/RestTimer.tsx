import { useState, useEffect, useCallback, useRef } from 'react';

interface Props {
  seconds?: number;
  onComplete: () => void;
  onDismiss: () => void;
}

/**
 * Ende der Pause melden. Vibration allein reicht nicht: liegt das Handy mit
 * gesperrtem Bildschirm auf der Bank, kommt sie nicht immer durch, und die
 * Seite bekommt ohnehin keine Rechenzeit. Eine Benachrichtigung stellt das
 * Betriebssystem zu.
 */
function melden(): void {
  if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
  try {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Pause vorbei', {
        body: 'N\u00e4chster Satz.',
        tag: 'fitness-pause',
        silent: false,
      });
    }
  } catch {
    // Auf iOS gibt es Notification in installierten Web-Apps nur eingeschraenkt.
    // Der Timer laeuft trotzdem richtig, nur die Meldung entfaellt.
  }
}

export default function RestTimer({ seconds = 90, onComplete, onDismiss }: Props) {
  const [remaining, setRemaining] = useState(seconds);
  const [isActive, setIsActive] = useState(true);
  const [isCompleted, setIsCompleted] = useState(false);
  /**
   * Zielzeitpunkt statt Restsekunden-Zaehler. Der Browser drosselt
   * setInterval, sobald das Handy sperrt oder der Tab in den Hintergrund
   * geht: der alte Zaehler stand dann still und zeigte nach dem Aufwecken
   * mitten in der naechsten Uebung noch Restzeit an.
   */
  const zielRef = useRef<number>(Date.now() + seconds * 1000);

  useEffect(() => {
    if (!isActive || isCompleted) return;

    const ablesen = () => {
      const uebrig = Math.max(0, Math.round((zielRef.current - Date.now()) / 1000));
      setRemaining(uebrig);
      if (uebrig === 0) {
        setIsActive(false);
        setIsCompleted(true);
        melden();
      }
    };

    ablesen();
    const interval = setInterval(ablesen, 500);
    // Beim Zurueckkehren sofort neu rechnen, nicht erst beim naechsten Takt.
    document.addEventListener('visibilitychange', ablesen);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', ablesen);
    };
  }, [isActive, isCompleted]);

  // Auto-dismiss after 2 seconds of completion
  useEffect(() => {
    if (!isCompleted) return;

    const timer = setTimeout(() => {
      onComplete();
    }, 2000);

    return () => clearTimeout(timer);
  }, [isCompleted, onComplete]);

  /** Verschiebt den Zielzeitpunkt, nicht die Anzeige: der naechste Takt
   *  rechnet aus dem Ziel und haette eine reine Anzeigeaenderung ueberschrieben. */
  const zeitAendern = useCallback((delta: number) => {
    const basis = Math.max(zielRef.current, Date.now());
    zielRef.current = Math.max(Date.now(), basis + delta * 1000);
    setRemaining(Math.max(0, Math.round((zielRef.current - Date.now()) / 1000)));
    if (delta > 0) {
      setIsActive(true);
      setIsCompleted(false);
    }
  }, []);

  const handleAddTime = useCallback(() => zeitAendern(15), [zeitAendern]);
  const handleSubtractTime = useCallback(() => zeitAendern(-15), [zeitAendern]);

  const handleSkip = useCallback(() => {
    onDismiss();
  }, [onDismiss]);

  const minutes = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const timeString = `${minutes}:${secs.toString().padStart(2, '0')}`;

  // Calculate circle progress
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  // Geklemmt: nach "+15" kann die Restzeit ueber der Vorgabe liegen, der
  // Kreisbogen lief dann ueber seinen eigenen Umfang hinaus.
  const progress = Math.min(1, remaining / Math.max(1, seconds)) * circumference;
  const strokeDashoffset = circumference - progress;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '24px',
        padding: '32px 20px',
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border)',
      }}
    >
      {/* Title */}
      <h2 style={{ margin: 0, color: 'var(--text)', fontSize: '1.25rem' }}>
        Pause
      </h2>

      {/* Circular Timer */}
      <div
        style={{
          position: 'relative',
          width: '180px',
          height: '180px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg
          width="180"
          height="180"
          style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}
        >
          {/* Background circle */}
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth="4"
          />
          {/* Progress circle */}
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke={isCompleted ? 'var(--success)' : 'var(--primary)'}
            strokeWidth="4"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s linear, stroke 0.3s ease' }}
          />
        </svg>

        {/* Time display */}
        <div
          style={{
            textAlign: 'center',
            zIndex: 10,
          }}
        >
          <div
            style={{
              fontSize: '3rem',
              fontWeight: 'bold',
              color: isCompleted ? 'var(--success)' : 'var(--primary)',
              fontFamily: 'monospace',
              transition: 'color 0.3s ease',
            }}
          >
            {timeString}
          </div>
          {isCompleted && (
            <div
              style={{
                fontSize: '0.9rem',
                color: 'var(--success)',
                marginTop: '8px',
                fontWeight: '500',
              }}
            >
              Fertig!
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      {!isCompleted && (
        <div
          style={{
            display: 'flex',
            gap: '12px',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
          }}
        >
          <button
            onClick={handleSubtractTime}
            style={{
              padding: '8px 16px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
            onMouseDown={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'var(--border)';
            }}
            onMouseUp={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)';
            }}
            onTouchStart={e => {
              const target = e.currentTarget as HTMLButtonElement;
              target.style.background = 'var(--border)';
            }}
            onTouchEnd={e => {
              const target = e.currentTarget as HTMLButtonElement;
              target.style.background = 'var(--bg-card)';
            }}
          >
            −15s
          </button>

          <button
            onClick={handleAddTime}
            style={{
              padding: '8px 16px',
              background: 'var(--primary)',
              border: 'none',
              color: '#fff',
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
            }}
            onMouseDown={e => {
              const btn = e.currentTarget as HTMLButtonElement;
              btn.style.opacity = '0.85';
            }}
            onMouseUp={e => {
              const btn = e.currentTarget as HTMLButtonElement;
              btn.style.opacity = '1';
            }}
            onTouchStart={e => {
              const btn = e.currentTarget as HTMLButtonElement;
              btn.style.opacity = '0.85';
            }}
            onTouchEnd={e => {
              const btn = e.currentTarget as HTMLButtonElement;
              btn.style.opacity = '1';
            }}
          >
            +15s
          </button>
        </div>
      )}

      {/* Skip button */}
      <button
        onClick={handleSkip}
        style={{
          padding: '10px 24px',
          background: 'transparent',
          border: '1px solid var(--text-muted)',
          color: 'var(--text-muted)',
          borderRadius: 'var(--radius)',
          cursor: 'pointer',
          fontSize: '0.95rem',
          fontWeight: '500',
          transition: 'all 0.2s ease',
          width: '100%',
          maxWidth: '200px',
        }}
        onMouseDown={e => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--border)';
        }}
        onMouseUp={e => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
        onTouchStart={e => {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.background = 'var(--border)';
        }}
        onTouchEnd={e => {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.background = 'transparent';
        }}
      >
        Überspringen
      </button>
    </div>
  );
}
