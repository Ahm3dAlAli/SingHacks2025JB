import { NextResponse } from "next/server";
import { generateAlertDetail } from "@/lib/mock/alerts";

export async function POST(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const d = generateAlertDetail(alertId);
  const rationale = {
    rules: d.ruleHits.map((r) => ({ id: r.id, name: r.name, contribution: r.score })),
    evidence: {
      transactions: d.transactions.slice(0, 2).map((t) => ({ id: t.id, amount: t.amount, cp: t.counterparty })),
      documents: d.documents.map((doc) => ({ id: doc.id, name: doc.name, anomaly: doc.anomaly ?? null })),
    },
    summary: `Risk ${d.risk} driven by ${d.ruleHits.map((r) => r.name).join(", ")}.`
  };
  return NextResponse.json({ id: d.id, rationale });
}

