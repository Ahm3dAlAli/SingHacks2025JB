import { NextResponse } from "next/server";
import { loadTransactions, computeRuleHits } from "@/lib/server/txData";

export async function POST(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const { byId } = await loadTransactions();
  const tx = byId.get(alertId);
  if (!tx) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const hits = computeRuleHits(tx);
  const rationale = {
    rules: hits.map((r) => ({ id: r.id, name: r.name, contribution: r.score })),
    evidence: {
      transactions: [{ id: tx.transaction_id, amount: tx.amount, cp: tx.display_counterparty || "" }],
      documents: [],
    },
    summary: `Risk drivers: ${hits.map((r) => r.name).join(", ")}.`,
  };
  return NextResponse.json({ id: tx.transaction_id, rationale });
}
