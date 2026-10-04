import { useState } from "react";
import { toast } from "sonner";
import { BrokerPanel } from "@/components/brokers/broker-panel";
import { ExecuteBar } from "@/components/execution/execute-bar";
import { ResultsPanel } from "@/components/execution/results-panel";
import { TopBar } from "@/components/layout/top-bar";
import { PortfolioPanel } from "@/components/portfolio/portfolio-panel";
import { useBrokers } from "@/hooks/useBrokers";
import { useExecution } from "@/hooks/useExecution";
import { DEMO_PORTFOLIO, newIdempotencyKey, parseSections, portfolioError, summarize, toText } from "@/lib/portfolio";
import type { Mode } from "@/lib/types";

export function Dashboard({ onLogout }: { onLogout: () => void }) {
  const { brokers, loading, connecting, connect } = useBrokers();
  const { execution, running, submit } = useExecution();
  const [broker, setBroker] = useState("mock");
  const [mode, setMode] = useState<Mode>("REBALANCE");
  const [text, setText] = useState(toText(DEMO_PORTFOLIO));

  const execute = () => {
    try {
      const sections = parseSections(text);
      submit({ ...sections, mode, broker, idempotency_key: newIdempotencyKey() });
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  return (
    <div className="min-h-screen">
      <TopBar onLogout={onLogout} />
      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Execute a portfolio</h1>
          <p className="mt-1 text-sm text-ink-2">Connect a broker, set the target, and place every trade in one click.</p>
        </div>

        <div className="grid items-start gap-6 lg:grid-cols-[380px_1fr]">
          <BrokerPanel brokers={brokers} loading={loading} connecting={connecting} onConnect={connect} />
          <PortfolioPanel
            brokers={brokers}
            broker={broker}
            mode={mode}
            text={text}
            onBrokerChange={setBroker}
            onModeChange={setMode}
            onTextChange={setText}
          />
        </div>

        <ExecuteBar
          broker={brokers.find((item) => item.broker === broker)}
          mode={mode}
          summary={summarize(text)}
          problem={portfolioError(text)}
          running={running}
          onExecute={execute}
        />

        {execution && <ResultsPanel execution={execution} />}
      </main>
    </div>
  );
}
