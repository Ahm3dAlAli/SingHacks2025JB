import { NextResponse } from "next/server";

export async function POST(request: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const body = await request.json().catch(() => ({}));
  const status = body?.status ?? "new";
  return NextResponse.json({ ok: true, id: alertId, status });
}
