import { ReactNode } from 'react';

interface ContainerProps {
  variant?: 'reading' | 'wide' | 'full';
  children: ReactNode;
  className?: string;
}

const variantStyles = {
  reading: 'max-w-3xl',
  wide:    'max-w-7xl',
  full:    'max-w-none',
};

export function Container({ variant = 'wide', children, className = '' }: ContainerProps) {
  return (
    <div className={`mx-auto px-6 ${variantStyles[variant]} ${className}`}>
      {children}
    </div>
  );
}
