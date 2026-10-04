import { cn } from "@/lib/cn";

interface SegmentedProps<T extends string> {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}

export function Segmented<T extends string>({ value, options, onChange }: SegmentedProps<T>) {
  return (
    <div role="radiogroup" className="flex h-10 w-full rounded-lg border border-line bg-subtle p-1">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex-1 rounded-md px-3 text-[13px] font-medium transition",
            value === option.value ? "bg-surface text-ink shadow-sm" : "text-ink-3 hover:text-ink",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
