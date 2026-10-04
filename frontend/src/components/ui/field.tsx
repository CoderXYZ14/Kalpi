import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  htmlFor?: string;
  children: ReactNode;
}

export function Field({ label, htmlFor, children }: FieldProps) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-[12px] font-medium tracking-wide text-ink-3 uppercase">
        {label}
      </label>
      {children}
    </div>
  );
}
