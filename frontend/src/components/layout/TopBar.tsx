'use client';

import Link from 'next/link';
import { ReactNode } from 'react';

interface TopBarProps {
  brand: ReactNode;            /* z.B. <Logo /> oder "lernen" */
  nav?: { label: string; href: string }[];
  actions?: ReactNode;         /* z.B. User-Menu, Search-Trigger */
}

export function TopBar({ brand, nav = [], actions }: TopBarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/85 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between gap-6">
        <Link
          href="/"
          className="font-serif text-xl font-semibold text-text-primary tracking-tight
            hover:text-accent transition-colors"
        >
          {brand}
        </Link>

        {nav.length > 0 && (
          <nav className="hidden md:flex items-center gap-1">
            {nav.map(item => (
              <Link
                key={item.href}
                href={item.href}
                className="px-3 py-2 text-sm text-text-secondary font-medium
                  rounded-lg transition-colors
                  hover:text-text-primary hover:bg-surface-hover"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-2">{actions}</div>
      </div>
    </header>
  );
}
