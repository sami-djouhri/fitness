import { ReactNode, HTMLAttributes } from 'react';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  variant?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

const variantStyles: Record<NonNullable<BadgeProps['variant']>, string> = {
  neutral: 'bg-surface-sunken text-text-secondary border-border',
  accent:  'bg-accent-soft text-accent border-accent/20',
  success: 'bg-success-soft text-success border-success/20',
  warning: 'bg-warning-soft text-warning border-warning/20',
  danger:  'bg-danger-soft text-danger border-danger/20',
  info:    'bg-info-soft text-info border-info/20',
};

const sizeStyles: Record<NonNullable<BadgeProps['size']>, string> = {
  sm: 'text-[11px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
};

export function Badge({
  children,
  variant = 'neutral',
  size = 'sm',
  className = '',
  ...props
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-full border
        ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
