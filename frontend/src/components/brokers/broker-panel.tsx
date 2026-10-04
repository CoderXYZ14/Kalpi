import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { Broker } from "@/lib/types";
import { BrokerRow } from "./broker-row";

interface BrokerPanelProps {
  brokers: Broker[];
  loading: boolean;
  connecting: string | null;
  onConnect: (broker: string) => void;
}

export function BrokerPanel({ brokers, loading, connecting, onConnect }: BrokerPanelProps) {
  const connectedCount = brokers.filter((broker) => broker.connected).length;
  return (
    <Card title="Brokers" description={loading ? "Loading..." : `${connectedCount} of ${brokers.length} connected`}>
      {loading ? (
        <div className="flex justify-center py-8 text-ink-3">
          <Spinner />
        </div>
      ) : (
        <ul className="-my-3 divide-y divide-line">
          {brokers.map((broker) => (
            <BrokerRow
              key={broker.broker}
              broker={broker}
              connecting={connecting === broker.broker}
              onConnect={() => onConnect(broker.broker)}
            />
          ))}
        </ul>
      )}
    </Card>
  );
}
