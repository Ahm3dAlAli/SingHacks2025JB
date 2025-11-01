import { NextResponse } from "next/server";
import { loadTransactions, computeRisk, computeRuleHits, computeSeverity } from "@/lib/server/txData";

export async function GET(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const { byId } = await loadTransactions();
  const tx = byId.get(alertId);
  if (!tx) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const ruleHits = computeRuleHits(tx);
  const risk = computeRisk(tx);
  const detail = {
    id: alertId,
    entity: tx.display_counterparty || tx.beneficiary_name || tx.originator_name,
    entityId: undefined,
    severity: computeSeverity(tx),
    status: "new" as const,
    ruleHits,
    transactions: [
      { id: tx.transaction_id, amount: tx.amount, currency: tx.currency, counterparty: tx.display_counterparty || "", ts: tx.booking_datetime },
    ],
    documents: [],
    risk,
  };
  return NextResponse.json(detail);
}
