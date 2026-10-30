import { ReactNode, ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'link';
  size?: 'sm' | 'md' | 'lg';
}

const variantStyles: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary:
    'bg-accent text-accent-foreground border border-accent ' +
    'hover:bg-accent-hover hover:border-accent-hover ' +
    'shadow-sm hover:shadow-md',
  secondary:
    'bg-surface text-text-primary border border-border ' +
    'hover:bg-surface-hover hover:border-border-strong ' +
    'shadow-xs',
  ghost:
    'bg-transparent text-text-secondary border border-transparent ' +
    'hover:text-text-primary hover:bg-surface-hover',
  danger:
    'bg-danger-soft text-danger border border-danger/20 ' +
    'hover:bg-danger hover:text-white hover:border-danger',
  link:
    'bg-transparent text-accent border-0 underline underline-offset-4 ' +
    'decoration-1 hover:text-accent-hover hover:decoration-2 px-0 py-0',
};

const sizeStyles: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'px-3 py-1.5 text-sm rounded-lg',
  md: 'px-4 py-2.5 text-sm rounded-lg',
  lg: 'px-6 py-3 text-base rounded-xl',
};

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ButtonProps) {
  const sizing = variant === 'link' ? '' : sizeStyles[size];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-medium
        transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
        active:scale-[0.98]
        ${variantStyles[variant]} ${sizing} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
