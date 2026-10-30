'use client';

import { ReactNode, useState } from 'react';

interface TooltipProps {
  label: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  children: ReactNode;
}

const sideStyles = {
  top:    'bottom-full mb-2 left-1/2 -translate-x-1/2',
  bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
  left:   'right-full mr-2 top-1/2 -translate-y-1/2',
  right:  'left-full ml-2 top-1/2 -translate-y-1/2',
};

export function Tooltip({ label, side = 'top', children }: TooltipProps) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          className={`absolute z-50 whitespace-nowrap rounded-md px-2.5 py-1.5
            text-xs text-text-primary bg-surface border border-border shadow-md
            ${sideStyles[side]}`}
        >
          {label}
        </span>
      )}
    </span>
  );
}
