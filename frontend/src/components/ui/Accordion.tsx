'use client';

import { ReactNode, useState } from 'react';

interface AccordionItem {
  id: string;
  title: ReactNode;
  content: ReactNode;
  meta?: ReactNode;
}

interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
  defaultOpen?: string[];
}

export function Accordion({ items, allowMultiple = false, defaultOpen = [] }: AccordionProps) {
  const [open, setOpen] = useState<Set<string>>(new Set(defaultOpen));

  const toggle = (id: string) => {
    setOpen(prev => {
      const next = new Set(prev);
      const isOpen = next.has(id);
      if (!allowMultiple) next.clear();
      if (!isOpen) next.add(id);
      return next;
    });
  };

  return (
    <div className="border border-border rounded-2xl bg-surface divide-y divide-border overflow-hidden">
      {items.map(item => {
        const isOpen = open.has(item.id);
        return (
          <div key={item.id}>
            <button
              type="button"
              aria-expanded={isOpen}
              onClick={() => toggle(item.id)}
              className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left
                hover:bg-surface-hover transition-colors"
            >
              <span className="font-medium text-text-primary">{item.title}</span>
              <span className="flex items-center gap-3 text-text-dim">
                {item.meta}
                <svg
                  className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="m4 6 4 4 4-4" />
                </svg>
              </span>
            </button>
            {isOpen && (
              <div className="px-5 pb-5 pt-1">{item.content}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
