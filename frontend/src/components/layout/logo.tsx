export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
        <rect width="32" height="32" rx="8" className="fill-ink" />
        <path d="M10 8v16M10 16l9-8M13 13.5L21 24" className="stroke-canvas" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight">Kalpi</p>
        <p className="text-[11px] text-ink-3">Execution Engine</p>
      </div>
    </div>
  );
}
