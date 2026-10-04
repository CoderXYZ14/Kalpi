import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export const fieldClass =
  "h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink placeholder:text-ink-3 transition focus:border-ink-3 focus:outline-none focus:ring-4 focus:ring-subtle";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldClass, className)} {...props} />;
}
