import { ButtonHTMLAttributes, ReactNode } from 'react';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;              /* aria-label, Pflicht */
  icon: ReactNode;
  variant?: 'ghost' | 'subtle';
  size?: 'sm' | 'md';
}

const variantStyles = {
  ghost:  'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
  subtle: 'text-text-secondary bg-surface-hover hover:bg-surface',
};

const sizeStyles = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
};

export function IconButton({
  label,
  icon,
  variant = 'ghost',
  size = 'md',
  className = '',
  ...props
}: IconButtonProps) {
  return (
    <button
      aria-label={label}
      className={`inline-flex items-center justify-center rounded-lg transition-colors
        active:scale-[0.96]
        ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {icon}
    </button>
  );
}
