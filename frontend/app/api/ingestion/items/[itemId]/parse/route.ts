import { NextResponse } from "next/server";
import { createParse, getItem } from "@/lib/mock/ingestion";

export async function POST(_: Request, ctx: { params: Promise<{ itemId: string }> }) {
  const { itemId } = await ctx.params;
  const item = getItem(itemId);
  if (!item) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const parse = createParse(itemId);
  return NextResponse.json({ parseId: parse.id, status: parse.status });
}

