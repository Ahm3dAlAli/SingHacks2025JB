import { NextResponse } from "next/server";
import { replaySuggestion } from "@/lib/mock/suggestions";

export async function POST(_: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return NextResponse.json(replaySuggestion(id));
}

