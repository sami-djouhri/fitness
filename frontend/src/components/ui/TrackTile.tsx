import Link from 'next/link';
import { ProgressBar } from './ProgressBar';

interface TrackTileProps {
  href: string;
  title: string;
  eyebrow?: string;
  accentClass?: string;     /* z.B. "bg-comptia-a-plus", app-spezifisch */
  progress?: number;        /* 0..100 */
  lessonsTotal?: number;
  lessonsDone?: number;
}

export function TrackTile({
  href,
  title,
  eyebrow,
  accentClass,
  progress,
  lessonsTotal,
  lessonsDone,
}: TrackTileProps) {
  return (
    <Link href={href} className="block group">
      <div className="relative rounded-2xl bg-surface border border-border shadow-sm overflow-hidden
        hover:shadow-md hover:border-border-strong transition-all duration-200">
        {accentClass && (
          <div className={`h-1.5 w-full ${accentClass}`} />
        )}
        <div className="p-6">
          {eyebrow && (
            <div className="text-xs uppercase tracking-[0.14em] text-text-dim font-medium mb-2">
              {eyebrow}
            </div>
          )}
          <h3 className="font-serif text-xl text-text-primary group-hover:text-accent transition-colors">
            {title}
          </h3>

          {(progress !== undefined || lessonsTotal !== undefined) && (
            <div className="mt-5 space-y-2">
              {progress !== undefined && (
                <ProgressBar value={progress} tone="accent" size="sm" />
              )}
              {lessonsTotal !== undefined && (
                <div className="flex items-center justify-between text-xs text-text-dim">
                  <span>
                    {lessonsDone ?? 0} von {lessonsTotal} Lessons
                  </span>
                  {progress !== undefined && <span>{Math.round(progress)}%</span>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
