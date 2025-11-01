import { NextResponse } from "next/server";
import { loadTransactions, computeRuleHits, computeRisk, computeSeverity } from "@/lib/server/txData";

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export async function GET(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const { byId } = await loadTransactions();
  const tx = byId.get(alertId);
  if (!tx) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const ruleHits = computeRuleHits(tx);
  const risk = computeRisk(tx);
  const counterpartyName = tx.display_counterparty || (tx.display_direction === "OUT" ? tx.beneficiary_name : tx.originator_name) || "";
  const entityId = counterpartyName ? `n-${slugify(counterpartyName)}` : undefined;
  const detail = {
    id: alertId,
    entity: counterpartyName || tx.beneficiary_name || tx.originator_name,
    entityId,
    severity: computeSeverity(tx),
    status: "new" as const,
    createdAt: tx.booking_datetime,
    risk,
    ruleHits,
    transactions: [
      { id: tx.transaction_id, amount: tx.amount, currency: tx.currency, counterparty: tx.display_counterparty || "", ts: tx.booking_datetime },
    ],
    documents: [],
  };
  return NextResponse.json(detail);
}
