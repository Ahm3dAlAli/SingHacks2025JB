import { NextResponse } from "next/server";
import { rejectSuggestion } from "@/lib/mock/suggestions";

export async function POST(_: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const s = rejectSuggestion(id);
  if (!s) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(s);
}

