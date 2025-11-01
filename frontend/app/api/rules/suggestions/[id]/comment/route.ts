import { NextResponse } from "next/server";
import { addComment } from "@/lib/mock/suggestions";

export async function POST(request: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const body = await request.json().catch(() => ({}));
  const s = addComment(id, body.author ?? "reviewer", String(body.text ?? ""));
  if (!s) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(s);
}

