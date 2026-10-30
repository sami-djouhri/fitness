import { ReactNode } from 'react';

interface LessonContentProps {
  children: ReactNode;
  className?: string;
}

/**
 * MDX-Wrapper. Aktiviert `prose-basis` (siehe theme.css) und sorgt für
 * Lese-Maximalbreite (~68ch).
 *
 * Verwendung in einer Lesson-Route:
 *
 *   <LessonContent>
 *     <MDXContent />
 *   </LessonContent>
 */
export function LessonContent({ children, className = '' }: LessonContentProps) {
  return (
    <article className={`prose-basis mx-auto max-w-reading ${className}`}>
      {children}
    </article>
  );
}
