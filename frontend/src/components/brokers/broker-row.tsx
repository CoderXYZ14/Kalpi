import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { brokerName, brokerNote } from "@/lib/brokers";
import type { Broker } from "@/lib/types";

interface BrokerRowProps {
  broker: Broker;
  connecting: boolean;
  onConnect: () => void;
}

function expiryText(value: string | null) {
  if (!value) return "";
  return `until ${new Date(value).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`;
}

export function BrokerRow({ broker, connecting, onConnect }: BrokerRowProps) {
  const name = brokerName(broker.broker);
  return (
    <li className="flex items-center gap-3 py-3">
      <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-subtle text-sm font-semibold text-ink-2">
        {name.charAt(0)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">{name}</p>
          {broker.connected && (
            <Badge tone="up" dot>
              Live
            </Badge>
          )}
          {!broker.configured && <Badge>Needs API keys</Badge>}
        </div>
        <p className="truncate text-[12px] text-ink-3">
          {!broker.configured
            ? "Add keys in .env to enable"
            : broker.connected
              ? expiryText(broker.token_expires_at)
              : brokerNote(broker.broker)}
        </p>
      </div>
      <Button
        size="sm"
        variant={broker.connected ? "ghost" : "secondary"}
        loading={connecting}
        disabled={!broker.configured}
        onClick={onConnect}
      >
        {broker.connected ? "Reconnect" : "Connect"}
      </Button>
    </li>
  );
}
