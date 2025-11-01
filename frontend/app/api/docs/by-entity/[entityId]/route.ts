import { NextResponse } from "next/server";
import { listByEntity } from "@/lib/server/docsStore";

export async function GET(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  const items = listByEntity(entityId);
  return NextResponse.json({ items });
}

