import { SelectHTMLAttributes, ReactNode, forwardRef } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
  children: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, className = '', children, ...props },
  ref,
) {
  const border = invalid ? 'border-danger' : 'border-border focus:border-accent';
  return (
    <select
      ref={ref}
      className={`h-11 rounded-lg border bg-surface-sunken px-4 pr-8 text-sm
        text-text-primary outline-none transition-colors appearance-none
        bg-[length:14px] bg-no-repeat bg-[right_12px_center]
        bg-[url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='none' stroke='%238c8475' stroke-width='2'><path d='m3 5 4 4 4-4'/></svg>")]
        ${border} ${className}`}
      {...props}
    >
      {children}
    </select>
  );
});
