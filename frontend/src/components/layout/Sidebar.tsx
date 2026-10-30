'use client';

import Link from 'next/link';
import { ReactNode } from 'react';

interface SidebarItem {
  href: string;
  label: string;
  icon?: ReactNode;
  badge?: string | number;
}

interface SidebarSection {
  title?: string;
  items: SidebarItem[];
}

interface SidebarProps {
  sections: SidebarSection[];
  activeHref?: string;
  className?: string;
}

export function Sidebar({ sections, activeHref, className = '' }: SidebarProps) {
  return (
    <aside
      className={`hidden lg:flex flex-col w-60 shrink-0 border-r border-border
        bg-bg/60 sticky top-16 self-start h-[calc(100vh-4rem)] overflow-y-auto py-6 ${className}`}
    >
      {sections.map((section, idx) => (
        <div key={idx} className={idx > 0 ? 'mt-6' : ''}>
          {section.title && (
            <div className="px-5 mb-2 text-xs uppercase tracking-[0.14em] text-text-dim font-medium">
              {section.title}
            </div>
          )}
          <nav className="flex flex-col gap-0.5 px-3">
            {section.items.map(item => {
              const active = item.href === activeHref;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
                    ${active
                      ? 'bg-accent-soft text-accent font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'}`}
                >
                  {item.icon && (
                    <span className={active ? 'text-accent' : 'text-text-dim'}>
                      {item.icon}
                    </span>
                  )}
                  <span className="flex-1">{item.label}</span>
                  {item.badge !== undefined && (
                    <span className="text-xs text-text-dim tabular-nums">{item.badge}</span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      ))}
    </aside>
  );
}
