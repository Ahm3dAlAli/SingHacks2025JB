import { NextResponse } from "next/server";
import { generateAlertDetail } from "@/lib/mock/alerts";

type Body = { alertIds?: string[] } | { alerts?: { id: string }[] };

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Body;
  const ids: string[] = Array.isArray((body as any).alertIds)
    ? (body as any).alertIds
    : Array.isArray((body as any).alerts)
    ? (body as any).alerts.map((a: any) => a.id)
    : [];

  const results = ids.map((id) => {
    const d = generateAlertDetail(id);
    const sevRank: Record<string, number> = { low: 0, medium: 1, high: 2, critical: 3 };
    const decision = d.risk >= 80 || sevRank[d.severity] >= 2 ? "escalate" : sevRank[d.severity] === 1 ? "hold" : "approve";
    const reason = decision === "escalate"
      ? `High risk ${d.risk} / severity ${d.severity}`
      : decision === "hold"
      ? `Moderate severity ${d.severity}`
      : `Low severity ${d.severity}`;
    return { id, decision, reason };
  });

  return NextResponse.json({ items: results });
}

