import { NextResponse } from "next/server";

export async function POST(request: Request) {
  // Accepts JSON batch or lines for demo; returns assigned IDs
  const body = await request.json().catch(() => ({}));
  const items = (body?.items ?? body?.transactions ?? []) as any[];
  const assigned = items.map((_, i) => ({ id: `ing-${Date.now()}-${i}` }));
  return NextResponse.json({ ok: true, items: assigned });
}

