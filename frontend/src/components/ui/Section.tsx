import { ReactNode } from 'react';

interface SectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ title, description, actions, children, className = '' }: SectionProps) {
  return (
    <section className={`mb-10 ${className}`}>
      {(title || description || actions) && (
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            {title && (
              <h2 className="font-serif text-2xl text-text-primary">{title}</h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-text-secondary">{description}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
