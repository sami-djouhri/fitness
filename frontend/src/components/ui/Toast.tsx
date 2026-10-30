'use client';

import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from 'react';

type ToastTone = 'neutral' | 'success' | 'warning' | 'danger';

interface ToastInput {
  title: string;
  description?: string;
  tone?: ToastTone;
  durationMs?: number;
}

interface ToastEntry extends Required<Pick<ToastInput, 'title' | 'tone'>> {
  id: string;
  description?: string;
}

interface ToastApi {
  show: (toast: ToastInput) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const toneStyles: Record<ToastTone, string> = {
  neutral: 'bg-surface border-border text-text-primary',
  success: 'bg-success-soft border-success/30 text-success',
  warning: 'bg-warning-soft border-warning/30 text-warning',
  danger:  'bg-danger-soft border-danger/30 text-danger',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastEntry[]>([]);

  const show = useCallback((t: ToastInput) => {
    const id = crypto.randomUUID();
    const entry: ToastEntry = {
      id,
      title: t.title,
      description: t.description,
      tone: t.tone ?? 'neutral',
    };
    setItems(prev => [...prev, entry]);
    const duration = t.durationMs ?? 5000;
    setTimeout(() => {
      setItems(prev => prev.filter(i => i.id !== id));
    }, duration);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <ToastViewport items={items} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

function ToastViewport({ items }: { items: ToastEntry[] }) {
  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none"
      role="region"
      aria-live="polite"
    >
      {items.map(item => (
        <div
          key={item.id}
          className={`pointer-events-auto rounded-xl border shadow-md px-4 py-3 min-w-[260px]
            ${toneStyles[item.tone]}`}
        >
          <div className="font-medium text-sm">{item.title}</div>
          {item.description && (
            <div className="text-xs opacity-80 mt-0.5">{item.description}</div>
          )}
        </div>
      ))}
    </div>
  );
}
