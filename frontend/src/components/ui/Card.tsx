import { ReactNode, HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'sunken' | 'accent' | 'outlined';
  interactive?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const variantStyles: Record<NonNullable<CardProps['variant']>, string> = {
  default:
    'bg-surface border border-border shadow-sm',
  sunken:
    'bg-surface-sunken border border-border',
  accent:
    'bg-accent-soft border border-accent/20',
  outlined:
    'bg-transparent border border-border-strong',
};

const paddingStyles: Record<NonNullable<CardProps['padding']>, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function Card({
  children,
  variant = 'default',
  interactive = false,
  padding = 'md',
  className = '',
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-2xl transition-all duration-200
        ${variantStyles[variant]}
        ${paddingStyles[padding]}
        ${interactive ? 'hover:shadow-md hover:border-border-strong cursor-pointer' : ''}
        ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`flex items-start justify-between gap-4 mb-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={`font-serif text-xl text-text-primary ${className}`}>
      {children}
    </h3>
  );
}

export function CardDescription({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <p className={`text-sm text-text-secondary mt-1 ${className}`}>
      {children}
    </p>
  );
}

export function CardFooter({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`flex items-center justify-between gap-3 mt-6 pt-4 border-t border-border ${className}`}>
      {children}
    </div>
  );
}
