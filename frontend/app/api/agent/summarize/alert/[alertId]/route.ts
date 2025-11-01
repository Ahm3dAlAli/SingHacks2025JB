import { NextResponse } from "next/server";
import { loadTransactions, computeRisk, computeSeverity, computeRuleHits } from "@/lib/server/txData";
import { maskAccount } from "@/lib/parseTransactions";

export async function POST(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const { byId } = await loadTransactions();
  const tx = byId.get(alertId);
  if (!tx) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const risk = computeRisk(tx);
  const severity = computeSeverity(tx);
  const hits = computeRuleHits(tx);
  const sevRank: Record<string, number> = { low: 0, medium: 1, high: 2, critical: 3 };
  const decision = risk >= 80 || sevRank[severity] >= 2 ? "escalate" : sevRank[severity] === 1 ? "hold" : "approve";
  const origin = tx.originator_name || maskAccount(tx.originator_account);
  const bene = tx.beneficiary_name || maskAccount(tx.beneficiary_account);
  const amt = Math.abs(tx.amount).toLocaleString();
  const summary = `(${tx.currency} ${amt}) ${origin} → ${bene}. Risk ${risk} (${severity}).`;
  return NextResponse.json({ id: tx.transaction_id, summary, recommendation: decision });
}
