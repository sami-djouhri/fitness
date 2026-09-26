import { InputHTMLAttributes, forwardRef } from 'react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, className = '', id, ...props },
  ref,
) {
  return (
    <label htmlFor={id} className={`inline-flex items-center gap-2 cursor-pointer text-sm text-text-primary ${className}`}>
      <input
        ref={ref}
        id={id}
        type="checkbox"
        className="peer sr-only"
        {...props}
      />
      <span
        className="w-5 h-5 rounded-md border border-border bg-surface-sunken
          grid place-items-center transition-all
          peer-checked:border-accent peer-checked:bg-accent
          peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-accent peer-focus-visible:outline-offset-2"
      >
        <svg className="w-3 h-3 text-accent-foreground opacity-0 peer-checked:opacity-100" viewBox="0 0 12 12" fill="none">
          <path d="m2 6 3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      {label && <span>{label}</span>}
    </label>
  );
});
