import { NextResponse } from "next/server";
import { validateSuggestion } from "@/lib/mock/suggestions";

export async function POST(_: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return NextResponse.json(validateSuggestion(id));
}

