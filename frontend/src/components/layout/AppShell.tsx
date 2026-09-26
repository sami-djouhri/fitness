import { ReactNode } from 'react';

interface AppShellProps {
  topBar?: ReactNode;
  sidebar?: ReactNode;
  bottomNav?: ReactNode;
  children: ReactNode;
  /** Inhaltsbreite. 'reading' für Lesson-Text, 'wide' für Dashboard. */
  variant?: 'wide' | 'reading';
  /** Footer-Markenname, default 'meisterminze' */
  brand?: string;
}

export function AppShell({
  topBar,
  sidebar,
  bottomNav,
  children,
  variant = 'wide',
  brand = 'meisterminze',
}: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-bg text-text-primary">
      {topBar}

      <div className="flex-1 flex">
        {sidebar}
        <main className="flex-1 min-w-0">
          <div
            className={`mx-auto px-6 py-10 pb-24 lg:pb-10
              ${variant === 'reading' ? 'max-w-3xl' : 'max-w-7xl'}`}
          >
            {children}
          </div>
        </main>
      </div>

      {bottomNav}

      <footer className="border-t border-border py-8 mt-16">
        <div className="mx-auto max-w-7xl px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-text-dim">
          <span className="font-serif">{brand}</span>
          <span>© {new Date().getFullYear()} {brand}</span>
        </div>
      </footer>
    </div>
  );
}
