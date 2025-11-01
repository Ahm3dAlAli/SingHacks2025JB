import crypto from "crypto";

export type AdverseItem = {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  date: string; // ISO
  category: string; // e.g., Fraud, Regulatory, Sanctions
  severity: "low" | "medium" | "high";
};

function seededRng(seed: string) {
  // Simple deterministic RNG based on SHA256
  let state = crypto.createHash("sha256").update(seed).digest();
  return () => {
    state = crypto.createHash("sha256").update(state).digest();
    return state.readUInt32BE(0) / 0xffffffff;
  };
}

const SOURCES = ["Financial Times", "Bloomberg", "Reuters", "Straits Times", "Channel NewsAsia", "SCMP", "The Business Times"];
const CATEGORIES = [
  { key: "Fraud investigation", weights: { low: 0.2, medium: 0.6, high: 0.2 } },
  { key: "Regulatory fine", weights: { low: 0.1, medium: 0.6, high: 0.3 } },
  { key: "Tax evasion report", weights: { low: 0.3, medium: 0.5, high: 0.2 } },
  { key: "Sanctions rumour", weights: { low: 0.4, medium: 0.4, high: 0.2 } },
  { key: "Adverse press", weights: { low: 0.6, medium: 0.3, high: 0.1 } },
  { key: "Court proceeding", weights: { low: 0.2, medium: 0.5, high: 0.3 } },
];

function pickWeighted(r: () => number, weights: Record<string, number>): keyof typeof weights {
  const entries = Object.entries(weights);
  const total = entries.reduce((a, [, w]) => a + w, 0);
  let x = r() * total;
  for (const [k, w] of entries) {
    if ((x -= w) <= 0) return k as any;
  }
  return entries[0][0] as any;
}

export function mockAdverseMediaForName(name: string) {
  const rng = seededRng(`adverse:${name}`);
  // Determine volume: 0-5 items, bias to 0-2
  const roll = rng();
  const count = roll < 0.2 ? 0 : roll < 0.6 ? 1 : roll < 0.85 ? 2 : roll < 0.95 ? 3 : 4 + Math.floor(rng() * 2);
  const items: AdverseItem[] = [];
  for (let i = 0; i < count; i++) {
    const catIdx = Math.floor(rng() * CATEGORIES.length);
    const cat = CATEGORIES[catIdx];
    // Title pattern determines severity per presentation rule:
    // - Title mentions client name  => high
    // - Title mentions 'watchlist'  => medium
    // - Otherwise                   => low
    const titleRoll = rng();
    let sev: "low" | "medium" | "high" = "low";
    let title: string;
    if (titleRoll < 0.45) {
      title = `${name} named in ${cat.key.toLowerCase()}`;
      sev = "high";
    } else if (titleRoll < 0.75) {
      title = `${cat.key}: ${name} added to watchlist`;
      sev = "medium";
    } else {
      title = `${cat.key} reported by regulators`;
      sev = "low";
    }
    const daysAgo = Math.floor(rng() * 540); // within ~18 months
    const date = new Date(Date.now() - daysAgo * 86400000).toISOString();
    const source = SOURCES[Math.floor(rng() * SOURCES.length)];
    const slug = crypto.createHash("md5").update(`${name}:${i}`).digest("hex").slice(0, 8);
    const summary = `${source} reported on ${cat.key.toLowerCase()} related to ${name}. Classification: ${sev === "high" ? "title directly mentions client" : sev === "medium" ? "mentions watchlist" : "indirect reference"}.`;
    const url = `https://example.com/${encodeURIComponent(name)}/${slug}`;
    items.push({ id: slug, title, summary, source, url, date, category: cat.key, severity: sev });
  }
  let risk: "low" | "medium" | "high" = "low";
  if (items.some((x) => x.severity === "high") || items.length >= 3) risk = "high";
  else if (items.some((x) => x.severity === "medium") || items.length >= 2) risk = "medium";
  const categories = Array.from(new Set(items.map((i) => i.category)));
  return { count: items.length, risk, items, categories };
}
