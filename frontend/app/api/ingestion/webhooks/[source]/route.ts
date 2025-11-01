import { NextResponse } from "next/server";

export async function POST(request: Request, ctx: { params: Promise<{ source: string }> }) {
  const { source } = await ctx.params;
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ ok: true, source, received: body });
}

