import { NextResponse } from "next/server";

export async function POST(request: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const body = await request.json().catch(() => ({}));
  const text = body?.text ?? "";
  return NextResponse.json({ ok: true, id: alertId, comment: { id: `${alertId}-c${Date.now()}`, text } });
}
