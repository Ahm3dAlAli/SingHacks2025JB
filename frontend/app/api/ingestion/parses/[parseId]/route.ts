import { NextResponse } from "next/server";
import { getParse } from "@/lib/mock/ingestion";

export async function GET(_: Request, ctx: { params: Promise<{ parseId: string }> }) {
  const { parseId } = await ctx.params;
  const parse = getParse(parseId);
  if (!parse) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(parse);
}

