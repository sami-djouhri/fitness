import { ReactNode } from 'react';

interface StatProps {
  label: string;
  value: string | number;
  hint?: string;
  delta?: {
    value: string;
    tone: 'success' | 'danger' | 'neutral';
  };
  icon?: ReactNode;
  className?: string;
}

const deltaTone = {
  success: 'text-success',
  danger:  'text-danger',
  neutral: 'text-text-dim',
};

export function Stat({ label, value, hint, delta, icon, className = '' }: StatProps) {
  return (
    <div
      className={`rounded-2xl bg-surface border border-border shadow-sm p-5
        flex flex-col gap-2 ${className}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-text-secondary font-medium">{label}</span>
        {icon && <span className="text-text-dim">{icon}</span>}
      </div>
      <div className="font-serif text-3xl text-text-primary tabular-nums">
        {value}
      </div>
      {delta && (
        <div className={`text-xs ${deltaTone[delta.tone]}`}>{delta.value}</div>
      )}
      {hint && (
        <div className="text-xs text-text-dim">{hint}</div>
      )}
    </div>
  );
}
