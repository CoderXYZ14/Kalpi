import { FlaskConical, ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Segmented } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { brokerName } from "@/lib/brokers";
import { DEMO_PORTFOLIO, FIRST_TIME_EXAMPLE, summarize, toText } from "@/lib/portfolio";
import type { Broker, Mode, Sections } from "@/lib/types";
import { CsvUploadButton } from "./csv-upload-button";

interface PortfolioPanelProps {
  brokers: Broker[];
  broker: string;
  mode: Mode;
  text: string;
  onBrokerChange: (broker: string) => void;
  onModeChange: (mode: Mode) => void;
  onTextChange: (text: string) => void;
}

const MODES: { value: Mode; label: string }[] = [
  { value: "FIRST_TIME", label: "First time" },
  { value: "REBALANCE", label: "Rebalance" },
];

export function PortfolioPanel({ brokers, broker, mode, text, onBrokerChange, onModeChange, onTextChange }: PortfolioPanelProps) {
  const load = (sections: Sections, nextMode: Mode) => {
    onTextChange(toText(sections));
    onModeChange(nextMode);
  };

  return (
    <Card
      title="Target portfolio"
      description="Explicit buy, sell and rebalance instructions"
      actions={
        <>
          <Button size="sm" icon={<FlaskConical className="size-3.5" />} onClick={() => load(DEMO_PORTFOLIO, "REBALANCE")}>
            Demo portfolio
          </Button>
          <Button size="sm" icon={<ShoppingCart className="size-3.5" />} onClick={() => load(FIRST_TIME_EXAMPLE, "FIRST_TIME")}>
            First-time example
          </Button>
          <CsvUploadButton onLoad={(sections) => load(sections, sections.sell || sections.rebalance ? "REBALANCE" : "FIRST_TIME")} />
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Mode">
          <Segmented value={mode} options={MODES} onChange={onModeChange} />
        </Field>
        <Field label="Broker" htmlFor="broker">
          <Select id="broker" value={broker} onChange={(event) => onBrokerChange(event.target.value)}>
            {brokers.map((item) => (
              <option key={item.broker} value={item.broker}>
                {brokerName(item.broker)}
                {item.connected ? "" : " (not connected)"}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-subtle">
        <textarea
          aria-label="Portfolio JSON"
          spellCheck={false}
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          className="block h-72 w-full resize-y bg-transparent p-4 font-mono text-[12.5px] leading-relaxed text-ink focus:outline-none"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-[12px] text-ink-3">
          <span className="num">{summarize(text)}</span>
          <span>
            CSV columns <span className="font-mono">section,symbol,quantity</span>
          </span>
        </div>
      </div>
    </Card>
  );
}
