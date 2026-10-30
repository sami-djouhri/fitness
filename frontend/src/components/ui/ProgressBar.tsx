interface ProgressBarProps {
  value: number;          /* 0..100 */
  max?: number;
  label?: string;
  showValue?: boolean;
  tone?: 'accent' | 'success' | 'warning' | 'danger' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const toneFill: Record<NonNullable<ProgressBarProps['tone']>, string> = {
  accent:  'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger:  'bg-danger',
  neutral: 'bg-text-dim',
};

const sizeHeight: Record<NonNullable<ProgressBarProps['size']>, string> = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-3.5',
};

export function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  tone = 'accent',
  size = 'md',
  className = '',
}: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className={className}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <span className="text-sm text-text-secondary font-medium">
              {label}
            </span>
          )}
          {showValue && (
            <span className="text-sm text-text-dim tabular-nums">
              {Math.round(pct)}%
            </span>
          )}
        </div>
      )}

      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className={`w-full rounded-full bg-surface-sunken overflow-hidden ${sizeHeight[size]}`}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${toneFill[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
