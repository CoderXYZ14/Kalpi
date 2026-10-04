import type { Sections } from "./types";

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

export function parseSections(text: string): Sections {
  let value: unknown;
  try {
    value = JSON.parse(text || "{}");
  } catch {
    throw new Error("Portfolio is not valid JSON");
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(
      "Portfolio must be a JSON object with buy, sell or rebalance lists",
    );
  }
  return value as Sections;
}

export function portfolioError(text: string): string | null {
  try {
    parseSections(text);
    return null;
  } catch (error) {
    return (error as Error).message;
  }
}

export function summarize(text: string): string {
  try {
    const sections = parseSections(text);
    const sells = sections.sell?.length ?? 0;
    const buys = sections.buy?.length ?? 0;
    const changes = sections.rebalance?.length ?? 0;
    const parts = [
      sells && `${sells} sell${sells > 1 ? "s" : ""}`,
      buys && `${buys} buy${buys > 1 ? "s" : ""}`,
      changes && `${changes} adjustment${changes > 1 ? "s" : ""}`,
    ].filter(Boolean);
    return parts.length ? parts.join(" · ") : "Empty portfolio";
  } catch (error) {
    return (error as Error).message;
  }
}

export function newIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === "function")
    return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
