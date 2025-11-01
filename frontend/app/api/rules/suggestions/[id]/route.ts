import { NextResponse } from "next/server";
import { getSuggestion } from "@/lib/mock/suggestions";

export async function GET(_: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const s = getSuggestion(id);
  if (!s) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(s);
}

