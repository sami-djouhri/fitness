/**
 * LessonCard: Beispiel-Komposition aus Card + Badge + ProgressBar.
 * Zeigt das design-system im echten Lernen-Kontext und ersetzt die
 * dunklen Track-Tile-Komponenten 1:1.
 */
import Link from 'next/link';
import { Card, CardTitle, CardDescription } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';

interface LessonCardProps {
  href: string;
  title: string;
  description?: string;
  trackLabel?: string;        /* z.B. "CompTIA A+" */
  durationMin?: number;
  progress?: number;          /* 0..100 */
  status?: 'new' | 'in-progress' | 'done';
}

const statusBadge = {
  'new':         { label: 'Neu',         variant: 'info'    as const },
  'in-progress': { label: 'Begonnen',    variant: 'accent'  as const },
  'done':        { label: 'Abgeschlossen', variant: 'success' as const },
};

export function LessonCard({
  href,
  title,
  description,
  trackLabel,
  durationMin,
  progress,
  status,
}: LessonCardProps) {
  const badge = status ? statusBadge[status] : null;

  return (
    <Link href={href} className="block group">
      <Card interactive padding="md" className="h-full flex flex-col">
        <div className="flex items-start justify-between gap-3 mb-3">
          {trackLabel && (
            <span className="text-xs uppercase tracking-[0.14em] text-text-dim font-medium">
              {trackLabel}
            </span>
          )}
          {badge && <Badge variant={badge.variant}>{badge.label}</Badge>}
        </div>

        <CardTitle className="group-hover:text-accent transition-colors">
          {title}
        </CardTitle>

        {description && (
          <CardDescription className="line-clamp-2">{description}</CardDescription>
        )}

        <div className="mt-auto pt-5 space-y-3">
          {typeof progress === 'number' && (
            <ProgressBar value={progress} size="sm" tone="accent" />
          )}
          {durationMin && (
            <div className="text-xs text-text-dim">≈ {durationMin} Min</div>
          )}
        </div>
      </Card>
    </Link>
  );
}
