import { NextResponse } from "next/server";
import { createSuggestionFromUpdate } from "@/lib/mock/suggestions";

export async function POST(_: Request, ctx: { params: Promise<{ updateId: string }> }) {
  const { updateId } = await ctx.params;
  const sug = createSuggestionFromUpdate(updateId);
  return NextResponse.json(sug);
}

