import { NextResponse } from "next/server";
import { generateTimeline } from "@/lib/mock/alerts";

export async function GET(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  return NextResponse.json(generateTimeline(alertId));
}
