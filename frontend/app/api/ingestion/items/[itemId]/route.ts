import { NextResponse } from "next/server";
import { getItem } from "@/lib/mock/ingestion";

export async function GET(_: Request, ctx: { params: Promise<{ itemId: string }> }) {
  const { itemId } = await ctx.params;
  const item = getItem(itemId);
  if (!item) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(item);
}

