'use client';

import { ReactNode, useEffect, useRef } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
  footer?: ReactNode;
}

const sizeStyles = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
};

export function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  children,
  footer,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={e => {
        if (e.target === ref.current) onClose();
      }}
      className={`w-full ${sizeStyles[size]} rounded-2xl bg-surface text-text-primary
        border border-border shadow-lg p-0
        backdrop:bg-black/40 backdrop:backdrop-blur-sm`}
    >
      <div className="p-6">
        {title && (
          <h2 className="font-serif text-2xl text-text-primary">{title}</h2>
        )}
        {description && (
          <p className="mt-1 text-sm text-text-secondary">{description}</p>
        )}
        {(title || description) && (
          <div className="mt-4" />
        )}
        {children}
      </div>
      {footer && (
        <div className="px-6 py-4 border-t border-border bg-surface-sunken flex items-center justify-end gap-3">
          {footer}
        </div>
      )}
    </dialog>
  );
}
