'use client';

import Link from 'next/link';
import { ReactNode } from 'react';

interface BottomNavItem {
  href: string;
  label: string;
  icon: ReactNode;
}

interface BottomNavProps {
  items: BottomNavItem[];
  activeHref?: string;
}

export function BottomNav({ items, activeHref }: BottomNavProps) {
  return (
    <nav
      className="lg:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border
        bg-bg/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]"
      aria-label="Hauptnavigation"
    >
      <ul className="flex items-center justify-around">
        {items.map(item => {
          const active = item.href === activeHref;
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={`flex flex-col items-center justify-center py-2.5 gap-0.5
                  ${active ? 'text-accent' : 'text-text-secondary'}`}
              >
                <span className="w-5 h-5">{item.icon}</span>
                <span className="text-[11px] font-medium">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
