interface SwitchProps {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
}

export function Switch({ checked, onCheckedChange, label, disabled, id }: SwitchProps) {
  return (
    <label htmlFor={id} className="inline-flex items-center gap-3 cursor-pointer select-none">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        id={id}
        onClick={() => onCheckedChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
          ${checked ? 'bg-accent' : 'bg-surface-sunken border border-border'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform
            ${checked ? 'translate-x-5' : 'translate-x-0.5'}`}
        />
      </button>
      {label && <span className="text-sm text-text-primary">{label}</span>}
    </label>
  );
}
