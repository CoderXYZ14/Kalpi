import { clsx } from "clsx";

export function FillBar({ filled, quantity }: { filled: number; quantity: number }) {
  const percent = quantity ? Math.min(100, Math.round((filled / quantity) * 100)) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-subtle">
        <div
          className={clsx("h-full rounded-full transition-all", percent === 100 ? "bg-up" : percent > 0 ? "bg-warn" : "bg-transparent")}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="num font-mono text-[12px] text-ink-2">
        {filled.toLocaleString()}/{quantity.toLocaleString()}
      </span>
    </div>
  );
}
