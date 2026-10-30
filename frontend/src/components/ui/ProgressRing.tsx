interface ProgressRingProps {
  value: number;          /* 0..100 */
  max?: number;
  size?: number;          /* px, default 80 */
  thickness?: number;     /* px, default 8 */
  tone?: 'accent' | 'success' | 'warning' | 'danger' | 'neutral';
  label?: string;         /* unter dem Ring */
  className?: string;
}

const toneColor = {
  accent:  'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger:  'var(--color-danger)',
  neutral: 'var(--color-text-dim)',
};

export function ProgressRing({
  value,
  max = 100,
  size = 80,
  thickness = 8,
  tone = 'accent',
  label,
  className = '',
}: ProgressRingProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const radius = (size - thickness) / 2;
  const circ = 2 * Math.PI * radius;
  const dash = (pct / 100) * circ;

  return (
    <div className={`inline-flex flex-col items-center gap-2 ${className}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          stroke="var(--color-surface-sunken)"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          strokeLinecap="round"
          stroke={toneColor[tone]}
          strokeDasharray={`${dash} ${circ - dash}`}
          style={{ transition: 'stroke-dasharray 500ms ease-out' }}
        />
        <text
          x="50%"
          y="50%"
          dy="0.36em"
          textAnchor="middle"
          transform={`rotate(90 ${size / 2} ${size / 2})`}
          className="font-serif font-semibold fill-current text-text-primary"
          fontSize={size * 0.24}
        >
          {Math.round(pct)}%
        </text>
      </svg>
      {label && <span className="text-xs text-text-dim">{label}</span>}
    </div>
  );
}
