import { NextResponse } from "next/server";

export async function POST(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  return NextResponse.json({ ok: true, id: alertId, status: "acknowledged" });
}
