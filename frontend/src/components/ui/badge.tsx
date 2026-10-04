import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type Tone = "up" | "down" | "warn" | "info" | "neutral";

const TONES: Record<Tone, string> = {
  up: "bg-up-soft text-up",
  down: "bg-down-soft text-down",
  warn: "bg-warn-soft text-warn",
  info: "bg-info-soft text-info",
  neutral: "bg-subtle text-ink-2",
};

interface BadgeProps {
  tone?: Tone;
  dot?: boolean;
  pulse?: boolean;
  className?: string;
  children: ReactNode;
}

export function Badge({ tone = "neutral", dot = false, pulse = false, className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide whitespace-nowrap uppercase",
        TONES[tone],
        className,
      )}
    >
      {dot && (
        <span className="relative flex size-1.5">
          {pulse && <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-60" />}
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  );
}
