import { ReactNode } from 'react';

type QuizOptionState = 'idle' | 'selected' | 'correct' | 'wrong' | 'revealed';

interface QuizOptionProps {
  label: ReactNode;
  state?: QuizOptionState;
  letter?: string;          /* A, B, C, D */
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

const stateStyles: Record<QuizOptionState, string> = {
  idle:     'bg-surface border-border hover:border-border-strong',
  selected: 'bg-accent-soft border-accent',
  correct:  'bg-success-soft border-success',
  wrong:    'bg-danger-soft border-danger',
  revealed: 'bg-success-soft border-success/40 ring-1 ring-success/30',
};

const letterStyles: Record<QuizOptionState, string> = {
  idle:     'bg-surface-sunken text-text-secondary border-border',
  selected: 'bg-accent text-accent-foreground border-accent',
  correct:  'bg-success text-white border-success',
  wrong:    'bg-danger text-white border-danger',
  revealed: 'bg-success text-white border-success',
};

export function QuizOption({
  label,
  state = 'idle',
  letter,
  onClick,
  disabled,
  className = '',
}: QuizOptionProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`w-full flex items-center gap-4 p-4 rounded-2xl border-2 text-left
        transition-all duration-200 disabled:cursor-not-allowed
        ${stateStyles[state]} ${className}`}
    >
      {letter && (
        <span
          className={`shrink-0 inline-flex items-center justify-center w-8 h-8 rounded-lg
            border font-serif text-sm font-semibold ${letterStyles[state]}`}
        >
          {letter}
        </span>
      )}
      <span className="text-text-primary leading-relaxed">{label}</span>
    </button>
  );
}
