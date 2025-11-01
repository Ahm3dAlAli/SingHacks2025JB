export type Transaction = {
  id: string;
  entityId: string;
  amount: number;
  currency: string;
  counterparty: string;
  ts: string;
  features: {
    velocity: number;
    geoRisk: number;
    amountZ: number;
  };
};

export type TxEvaluation = {
  ruleHits: { id: string; name: string; score: number }[];
  score: number;
  decision: "approve" | "hold" | "escalate";
};

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

const currencies = ["USD", "SGD", "HKD", "EUR", "GBP"];
const cps = ["ACME Ltd.", "Foo Bar Co.", "Globex", "Initech", "Stark Trading", "Wayne Holdings"];

export function generateTransaction(id: string): Transaction {
  const seed = seededNumber(id);
  const entityId = `p-${(seed % 8) + 1}`;
  const amount = Math.round((seed % 200_000) + 100) + (seed % 2 ? 0.5 : 0);
  const currency = currencies[seed % currencies.length];
  const counterparty = cps[seed % cps.length];
  const ts = new Date(Date.now() - ((seed % 72) + 1) * 3600_000).toISOString();
  const features = {
    velocity: (seed % 100) / 100, // 0..1
    geoRisk: ((seed >> 3) % 100) / 100,
    amountZ: ((amount % 10000) - 5000) / 2000, // -2.5..2.5 approx
  };
  return { id, entityId, amount, currency, counterparty, ts, features };
}

export function listTransactionsForEntity(entityId: string, limit = 10): Transaction[] {
  const baseSeed = seededNumber(entityId);
  return Array.from({ length: limit }, (_, i) => generateTransaction(`${entityId}-tx-${(baseSeed + i) % 1000}`));
}

export function evaluateTx(payload: Partial<Transaction>): TxEvaluation {
  const amt = payload.amount ?? 0;
  const velocity = payload.features?.velocity ?? 0;
  const geo = payload.features?.geoRisk ?? 0;
  const hits: { id: string; name: string; score: number }[] = [];
  if (amt > 100_000) hits.push({ id: "r-high-amt", name: "High amount", score: Math.min(40, Math.round((amt - 100_000) / 5_000)) });
  if (velocity > 0.7) hits.push({ id: "r-velocity", name: "Velocity anomaly", score: Math.round(velocity * 30) });
  if (geo > 0.6) hits.push({ id: "r-geo", name: "Geo-risk region", score: Math.round(geo * 25) });
  const score = hits.reduce((s, h) => s + h.score, 0);
  const decision = score >= 60 ? "escalate" : score >= 25 ? "hold" : "approve";
  return { ruleHits: hits, score, decision };
}

export function entityScoreTrend(entityId: string) {
  const seed = seededNumber(entityId);
  const base = 20 + (seed % 60);
  const points = Array.from({ length: 8 }, (_, i) => ({
    ts: new Date(Date.now() - i * 24 * 3600_000).toISOString(),
    score: Math.max(0, Math.min(100, base + ((seed >> i) % 15) - 7)),
  })).reverse();
  return { current: points[points.length - 1].score, trend: points };
}

