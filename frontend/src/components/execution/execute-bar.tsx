import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { brokerName } from "@/lib/brokers";
import type { Broker, Mode } from "@/lib/types";

interface ExecuteBarProps {
  broker: Broker | undefined;
  mode: Mode;
  summary: string;
  problem: string | null;
  running: boolean;
  onExecute: () => void;
}

export function ExecuteBar({ broker, mode, summary, problem, running, onExecute }: ExecuteBarProps) {
  const blocker = !broker?.connected ? "Connect this broker first, then execute." : problem;
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-line bg-surface px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium">
          {mode === "REBALANCE" ? "Rebalance" : "First-time buy"} on {broker ? brokerName(broker.broker) : "—"}
        </p>
        {blocker ? (
          <p className="mt-0.5 text-[13px] text-down">{blocker}</p>
        ) : (
          <p className="num mt-0.5 text-[13px] text-ink-3">{summary} · Sells run before buys, max 8 orders/sec</p>
        )}
      </div>
      <Button variant="primary" size="lg" loading={running} disabled={Boolean(blocker)} icon={<Play className="size-4" />} onClick={onExecute}>
        {running ? "Executing" : "Execute"}
      </Button>
    </div>
  );
}
