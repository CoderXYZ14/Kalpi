import { Badge, type Tone } from "@/components/ui/badge";
import type { ExecutionStatus, OrderStatus } from "@/lib/types";

export const STATUS_TONE: Record<OrderStatus | ExecutionStatus, Tone> = {
  SUCCESS: "up",
  COMPLETED: "up",
  PARTIAL: "warn",
  PENDING: "info",
  PLACED: "info",
  RUNNING: "info",
  FAILED: "down",
  STOPPED: "down",
  SKIPPED: "neutral",
  QUEUED: "neutral",
};

export function StatusBadge({ status }: { status: OrderStatus | ExecutionStatus }) {
  const live = status === "RUNNING" || status === "PLACED";
  return (
    <Badge tone={STATUS_TONE[status]} dot pulse={live}>
      {status}
    </Badge>
  );
}
