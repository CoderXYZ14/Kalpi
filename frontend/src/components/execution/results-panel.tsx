import { CircleAlert } from "lucide-react";
import { Card } from "@/components/ui/card";
import { brokerName } from "@/lib/brokers";
import type { Execution } from "@/lib/types";
import { OrdersTable } from "./orders-table";
import { StatStrip } from "./stat-strip";
import { StatusBadge } from "./status-badge";

function duration(execution: Execution) {
  const end = execution.finished_at ? new Date(execution.finished_at) : new Date();
  const seconds = Math.max(0, Math.round((end.getTime() - new Date(execution.created_at).getTime()) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function ResultsPanel({ execution }: { execution: Execution }) {
  const mode = execution.mode === "REBALANCE" ? "Rebalance" : "First-time buy";
  return (
    <div className="animate-rise">
      <Card
        title={
          <span className="flex items-center gap-2.5">
            Execution <StatusBadge status={execution.status} />
          </span>
        }
        description={
          <span className="num">
            {mode} on {brokerName(execution.broker)} · <span className="font-mono">{execution.id.slice(0, 8)}</span> · {duration(execution)}
          </span>
        }
        actions={execution.status === "RUNNING" && <span className="text-[12px] text-ink-3">Live · refreshing every 2s</span>}
      >
        <div className="grid gap-4">
          {execution.error_message && (
            <div className="flex gap-2.5 rounded-xl bg-down-soft px-4 py-3 text-[13px] text-down">
              <CircleAlert className="mt-0.5 size-4 shrink-0" />
              <p>{execution.error_message}</p>
            </div>
          )}
          <StatStrip counts={execution.counts} total={execution.orders.length} />
          <OrdersTable orders={execution.orders} />
        </div>
      </Card>
    </div>
  );
}
