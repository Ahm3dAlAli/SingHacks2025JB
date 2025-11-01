import { NextResponse } from "next/server";
import { decide, getById, type AppRole } from "@/lib/server/docsStore";

export async function GET(_: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const item = getById(id);
  if (!item) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(item);
}

export async function POST(request: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const body = (await request.json().catch(() => ({}))) as { action?: string; note?: string; role?: AppRole; fraud?: boolean };
  const action = body.action as "approve" | "reject" | "escalate" | undefined;
  if (!action) return NextResponse.json({ error: "Missing action" }, { status: 400 });
  const role = (body.role || "compliance_manager") as AppRole;
  const item = decide(id, role, action, body.note, !!body.fraud);
  if (!item) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ ok: true, item });
}
