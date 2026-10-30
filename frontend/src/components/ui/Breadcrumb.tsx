import Link from 'next/link';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumb({ items, className = '' }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={`text-sm ${className}`}>
      <ol className="flex items-center gap-2 flex-wrap text-text-dim">
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-2">
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="hover:text-text-primary transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span className={isLast ? 'text-text-primary font-medium' : ''}>
                  {item.label}
                </span>
              )}
              {!isLast && (
                <span aria-hidden="true" className="text-text-dim">›</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
