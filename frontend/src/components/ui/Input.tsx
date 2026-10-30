import { InputHTMLAttributes, ReactNode, forwardRef } from 'react';

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: 'sm' | 'md' | 'lg';
  invalid?: boolean;
  leading?: ReactNode;
  trailing?: ReactNode;
}

const sizeStyles = {
  sm: 'h-9 text-sm px-3',
  md: 'h-11 text-sm px-4',
  lg: 'h-12 text-base px-4',
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { size = 'md', invalid, leading, trailing, className = '', ...props },
  ref,
) {
  const wrapperBorder = invalid ? 'border-danger' : 'border-border focus-within:border-accent';
  return (
    <div
      className={`flex items-center gap-2 rounded-lg bg-surface-sunken border transition-colors
        ${wrapperBorder} ${className}`}
    >
      {leading && <span className="pl-3 text-text-dim">{leading}</span>}
      <input
        ref={ref}
        className={`flex-1 bg-transparent outline-none text-text-primary placeholder:text-text-dim
          ${sizeStyles[size]} ${leading ? 'pl-1' : ''} ${trailing ? 'pr-1' : ''}`}
        {...props}
      />
      {trailing && <span className="pr-3 text-text-dim">{trailing}</span>}
    </div>
  );
});
