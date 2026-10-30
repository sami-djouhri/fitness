interface AvatarProps {
  src?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'w-7 h-7 text-[11px]',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-base',
};

function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase() ?? '')
    .join('');
}

export function Avatar({ src, name, size = 'md', className = '' }: AvatarProps) {
  const cls = `inline-flex items-center justify-center rounded-full overflow-hidden font-medium
    bg-accent-soft text-accent ${sizeStyles[size]} ${className}`;

  if (src) {
    return (
      <img src={src} alt={name} className={cls} />
    );
  }
  return (
    <span aria-label={name} className={cls}>
      {initials(name) || '?'}
    </span>
  );
}
