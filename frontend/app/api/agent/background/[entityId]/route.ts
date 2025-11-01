import { NextResponse } from "next/server";
import { generateBackgroundReport } from "@/lib/mock/entities";

export async function POST(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  return NextResponse.json(generateBackgroundReport(entityId));
}

