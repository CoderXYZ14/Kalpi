const BROKERS: Record<string, { name: string; note: string }> = {
  mock: { name: "Mock broker", note: "Simulated · connects instantly" },
  zerodha: { name: "Zerodha", note: "Kite Connect login" },
  groww: { name: "Groww", note: "API key approval" },
  upstox: { name: "Upstox", note: "OAuth login" },
  fyers: { name: "Fyers", note: "OAuth login" },
  angelone: { name: "Angel One", note: "SmartAPI login" },
};

export function brokerName(broker: string): string {
  return BROKERS[broker]?.name ?? broker;
}

export function brokerNote(broker: string): string {
  return BROKERS[broker]?.note ?? "";
}
