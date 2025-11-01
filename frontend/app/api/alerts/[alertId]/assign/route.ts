import { NextResponse } from "next/server";

export async function POST(request: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const body = await request.json().catch(() => ({}));
  const assignee = body?.assignee ?? "demo.user";
  const sla = body?.sla ?? { hours: 24 };
  return NextResponse.json({ ok: true, id: alertId, assignee, sla });
}
