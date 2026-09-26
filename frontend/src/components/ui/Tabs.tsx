interface TabItem {
  value: string;
  label: string;
  count?: number;
}

interface TabsProps {
  value: string;
  onChange: (value: string) => void;
  items: TabItem[];
  className?: string;
}

export function Tabs({ value, onChange, items, className = '' }: TabsProps) {
  return (
    <div role="tablist" className={`flex items-center gap-1 border-b border-border ${className}`}>
      {items.map(item => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={`relative px-4 py-3 text-sm font-medium transition-colors
              ${active ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            <span className="inline-flex items-center gap-2">
              {item.label}
              {item.count !== undefined && (
                <span className="text-xs text-text-dim tabular-nums">
                  {item.count}
                </span>
              )}
            </span>
            {active && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
