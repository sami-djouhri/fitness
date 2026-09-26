import { TextareaHTMLAttributes, forwardRef } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className = '', rows = 4, ...props },
  ref,
) {
  const border = invalid ? 'border-danger' : 'border-border focus:border-accent';
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={`w-full rounded-lg border bg-surface-sunken px-4 py-3 text-sm
        text-text-primary placeholder:text-text-dim outline-none transition-colors resize-y
        ${border} ${className}`}
      {...props}
    />
  );
});
