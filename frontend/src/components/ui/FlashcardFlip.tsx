'use client';

import { ReactNode } from 'react';

interface FlashcardFlipProps {
  front: ReactNode;
  back: ReactNode;
  flipped: boolean;
  onFlip: () => void;
  className?: string;
}

export function FlashcardFlip({ front, back, flipped, onFlip, className = '' }: FlashcardFlipProps) {
  return (
    <button
      type="button"
      onClick={onFlip}
      aria-label={flipped ? 'Vorderseite anzeigen' : 'Rückseite anzeigen'}
      className={`w-full block group ${className}`}
      style={{ perspective: '1200px' }}
    >
      <div
        className="relative w-full aspect-[3/2] transition-transform duration-500"
        style={{
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
        }}
      >
        <div
          className="absolute inset-0 rounded-2xl bg-surface border border-border shadow-sm
            p-8 flex items-center justify-center text-center"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <div className="font-serif text-2xl text-text-primary">{front}</div>
        </div>
        <div
          className="absolute inset-0 rounded-2xl bg-accent-soft border border-accent/30 shadow-sm
            p-8 flex items-center justify-center text-center"
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          <div className="text-base text-text-primary leading-relaxed">{back}</div>
        </div>
      </div>
    </button>
  );
}
