import { NextResponse } from "next/server";
import { generateAlertDetail } from "@/lib/mock/alerts";

export async function GET(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  return NextResponse.json(generateAlertDetail(alertId));
}
