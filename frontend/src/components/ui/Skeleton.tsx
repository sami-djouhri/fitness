interface SkeletonProps {
  width?: string;
  height?: string;
  rounded?: 'md' | 'lg' | 'full';
  className?: string;
}

const roundedStyles = {
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

export function Skeleton({
  width = '100%',
  height = '1rem',
  rounded = 'md',
  className = '',
}: SkeletonProps) {
  return (
    <div
      className={`bg-surface-sunken animate-pulse ${roundedStyles[rounded]} ${className}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
