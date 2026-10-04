import { clsx } from "clsx";
import { TONE_TEXT } from "@/components/ui/badge";
import type { OrderStatus } from "@/lib/types";
import { STATUS_TONE } from "./status-badge";

const ORDER: OrderStatus[] = ["SUCCESS", "PARTIAL", "PENDING", "FAILED", "SKIPPED", "PLACED", "QUEUED"];

export function StatStrip({ counts, total }: { counts: Partial<Record<OrderStatus, number>>; total: number }) {
  const present = ORDER.filter((status) => counts[status]);
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] gap-px overflow-hidden rounded-xl border border-line bg-line">
      <div className="bg-surface px-4 py-3">
        <p className="text-[11px] font-medium tracking-wide text-ink-3 uppercase">Orders</p>
        <p className="num mt-1 text-2xl font-semibold tracking-tight">{total}</p>
      </div>
      {present.map((status) => (
        <div key={status} className="bg-surface px-4 py-3">
          <p className="text-[11px] font-medium tracking-wide text-ink-3 uppercase">{status.toLowerCase()}</p>
          <p className={clsx("num mt-1 text-2xl font-semibold tracking-tight", TONE_TEXT[STATUS_TONE[status]])}>{counts[status]}</p>
        </div>
      ))}
    </div>
  );
}
