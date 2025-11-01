import { NextResponse } from "next/server";
import { generateAlertDetail } from "@/lib/mock/alerts";

export async function POST(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const d = generateAlertDetail(alertId);
  // Simple policy: risk >= 80 or severity high/critical → escalate, medium → hold, else approve.
  const sevRank: Record<string, number> = { low: 0, medium: 1, high: 2, critical: 3 };
  const decision = d.risk >= 80 || sevRank[d.severity] >= 2 ? "escalate" : sevRank[d.severity] === 1 ? "hold" : "approve";
  const summary = `Alert ${d.id} for ${d.entity} scored ${d.risk} (${d.severity}). Top patterns: ${d.ruleHits
    .map((r) => `${r.name} (${r.score})`)
    .join(", ")}. Recommendation: ${decision}.`;
  return NextResponse.json({ id: d.id, summary, recommendation: decision });
}

