import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { clsx } from "clsx";
import type { Order } from "@/lib/types";
import { FillBar } from "./fill-bar";
import { StatusBadge } from "./status-badge";

const HEAD = "px-4 py-2.5 text-left text-[11px] font-medium tracking-wide text-ink-3 uppercase";

export function OrdersTable({ orders }: { orders: Order[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full min-w-[720px] text-sm">
        <thead className="bg-subtle">
          <tr>
            <th className={HEAD}>#</th>
            <th className={HEAD}>Symbol</th>
            <th className={HEAD}>Side</th>
            <th className={clsx(HEAD, "text-right")}>Qty</th>
            <th className={HEAD}>Filled</th>
            <th className={HEAD}>Status</th>
            <th className={HEAD}>Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {orders.map((order) => (
            <tr key={order.tag} className="align-top transition hover:bg-subtle/60">
              <td className="num px-4 py-3 font-mono text-[12px] text-ink-3">{order.sequence}</td>
              <td className="px-4 py-3 font-mono text-[13px] font-medium">{order.symbol}</td>
              <td className="px-4 py-3">
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 text-[12px] font-semibold",
                    order.side === "BUY" ? "text-up" : "text-down",
                  )}
                >
                  {order.side === "BUY" ? <ArrowUpRight className="size-3.5" /> : <ArrowDownRight className="size-3.5" />}
                  {order.side}
                </span>
              </td>
              <td className="num px-4 py-3 text-right font-mono text-[13px]">{order.quantity.toLocaleString()}</td>
              <td className="px-4 py-3">
                <FillBar filled={order.filled_quantity} quantity={order.quantity} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={order.status} />
              </td>
              <td className="max-w-xs px-4 py-3">
                {order.error_code && <p className="font-mono text-[11px] font-semibold text-ink-2">{order.error_code}</p>}
                {order.error_message && <p className="text-[12px] leading-snug text-ink-3">{order.error_message}</p>}
                {!order.error_code && !order.error_message && <span className="text-ink-3">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
