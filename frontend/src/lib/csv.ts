import type { Sections } from "./types";

const SECTIONS = ["buy", "sell", "rebalance"] as const;

export function parseCsv(text: string): Sections {
  const rows: Required<Sections> = { buy: [], sell: [], rebalance: [] };
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  lines.forEach((line, index) => {
    const [section = "", symbol = "", quantity = ""] = line.split(",").map((cell) => cell.trim());
    const key = section.toLowerCase();
    if (index === 0 && key === "section") return;
    if (!SECTIONS.includes(key as (typeof SECTIONS)[number])) {
      throw new Error(`CSV line ${index + 1}: section must be buy, sell or rebalance`);
    }
    const value = Number(quantity);
    if (!symbol || quantity === "" || !Number.isInteger(value)) {
      throw new Error(`CSV line ${index + 1}: needs a symbol and a whole-number quantity`);
    }
    if (key === "rebalance") rows.rebalance.push({ symbol, quantity_change: value });
    else rows[key as "buy" | "sell"].push({ symbol, quantity: value });
  });

  const sections: Sections = {};
  if (rows.sell.length) sections.sell = rows.sell;
  if (rows.buy.length) sections.buy = rows.buy;
  if (rows.rebalance.length) sections.rebalance = rows.rebalance;
  if (!Object.keys(sections).length) throw new Error("CSV has no rows");
  return sections;
}
