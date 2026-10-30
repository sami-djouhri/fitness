import { ReactNode } from 'react';

type StateTone = 'neutral' | 'loading' | 'empty' | 'error';

interface StatePanelProps {
  tone?: StateTone;
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

const toneStyles: Record<StateTone, string> = {
  neutral: 'border-border bg-surface',
  loading: 'border-border bg-surface',
  empty:   'border-dashed border-border bg-surface-sunken',
  error:   'border-danger/30 bg-danger-soft',
};

const iconWrap: Record<StateTone, string> = {
  neutral: 'bg-surface-sunken text-text-secondary',
  loading: 'bg-accent-soft text-accent',
  empty:   'bg-surface text-text-dim border border-border',
  error:   'bg-white text-danger',
};

export function StatePanel({
  tone = 'neutral',
  icon,
  title,
  description,
  action,
  className = '',
}: StatePanelProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`rounded-2xl border px-8 py-12 text-center
        ${toneStyles[tone]} ${className}`}
    >
      {icon && (
        <div
          className={`inline-flex items-center justify-center
            w-14 h-14 rounded-2xl mb-5 ${iconWrap[tone]}
            ${tone === 'loading' ? 'animate-pulse' : ''}`}
        >
          {icon}
        </div>
      )}

      <h3 className="font-serif text-2xl text-text-primary">{title}</h3>

      {description && (
        <p className="mt-2 text-text-secondary max-w-md mx-auto leading-relaxed">
          {description}
        </p>
      )}

      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}
