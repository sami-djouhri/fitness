import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;             /* Kleine Kategorie über dem Titel */
  actions?: ReactNode;
  children?: ReactNode;         /* Optionaler Slot unter description */
  align?: 'left' | 'center';
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  children,
  align = 'left',
}: PageHeaderProps) {
  return (
    <header
      className={`mb-10 pb-6 border-b border-border
        ${align === 'center' ? 'text-center' : ''}`}
    >
      <div
        className={`flex flex-col gap-4
          ${align === 'left' ? 'sm:flex-row sm:items-end sm:justify-between' : 'items-center'}`}
      >
        <div className={align === 'center' ? 'max-w-2xl mx-auto' : 'max-w-3xl'}>
          {eyebrow && (
            <div className="text-xs uppercase tracking-[0.18em] text-accent font-medium mb-3">
              {eyebrow}
            </div>
          )}

          <h1 className="font-serif text-4xl sm:text-[2.5rem] leading-tight text-text-primary">
            {title}
          </h1>

          {description && (
            <p className="mt-3 text-lg text-text-secondary leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {actions && (
          <div className={`flex items-center gap-3
            ${align === 'left' ? 'shrink-0' : 'justify-center'}`}>
            {actions}
          </div>
        )}
      </div>

      {children && <div className="mt-6">{children}</div>}
    </header>
  );
}
