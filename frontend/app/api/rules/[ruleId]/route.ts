import { NextResponse } from "next/server";
import { getRule } from "@/lib/mock/rules";

export async function GET(_: Request, ctx: { params: Promise<{ ruleId: string }> }) {
  const { ruleId } = await ctx.params;
  return NextResponse.json(getRule(ruleId));
}

