import type { Mode, Sections } from "./types";

export const DEMO_PORTFOLIO: Sections = {
  sell: [
    { symbol: "INFY", quantity: 5 },
    { symbol: "TESTNOSELL", quantity: 2 },
    { symbol: "HDFCBANK", quantity: 999 },
    { symbol: "TESTCIRCUIT", quantity: 3 },
  ],
  buy: [
    { symbol: "TESTNOTALLOWED", quantity: 1 },
    { symbol: "TESTPARTIAL", quantity: 10 },
    { symbol: "TESTRATELIMIT", quantity: 1 },
    { symbol: "TESTTIMEOUT", quantity: 2 },
    { symbol: "RELIANCE", quantity: 100000 },
  ],
  rebalance: [
    { symbol: "TCS", quantity_change: -3 },
    { symbol: "WIPRO", quantity_change: 4 },
  ],
};

export const FIRST_TIME_EXAMPLE: Sections = {
  buy: [
    { symbol: "INFY", quantity: 10 },
    { symbol: "TCS", quantity: 5 },
    { symbol: "HDFCBANK", quantity: 8 },
  ],
};

export function toText(sections: Sections): string {
  return JSON.stringify(sections, null, 2);
}

export const MODE_LABEL: Record<Mode, string> = {
  FIRST_TIME: "First-time buy",
  REBALANCE: "Rebalance",
};

function count(n: number, word: string) {
  return n ? `${n} ${word}${n > 1 ? "s" : ""}` : "";
}

export function checkPortfolio(text: string): { sections?: Sections; error?: string; summary: string } {
  let value: unknown;
  try {
    value = JSON.parse(text || "{}");
  } catch {
    return { error: "Portfolio is not valid JSON", summary: "Portfolio is not valid JSON" };
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    const error = "Portfolio must be a JSON object with buy, sell or rebalance lists";
    return { error, summary: error };
  }
  const sections = value as Sections;
  const parts = [
    count(sections.sell?.length ?? 0, "sell"),
    count(sections.buy?.length ?? 0, "buy"),
    count(sections.rebalance?.length ?? 0, "adjustment"),
  ].filter(Boolean);
  return { sections, summary: parts.length ? parts.join(" · ") : "Empty portfolio" };
}

export function newIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === "function")
    return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
