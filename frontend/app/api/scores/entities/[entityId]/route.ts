import { NextResponse } from "next/server";
import { entityScoreTrend } from "@/lib/mock/transactions";

export async function GET(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  return NextResponse.json(entityScoreTrend(entityId));
}

