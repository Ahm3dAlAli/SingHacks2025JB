import { NextResponse } from "next/server";
import { versionDiff } from "@/lib/mock/rules";

export async function GET(_: Request, ctx: { params: Promise<{ versionId: string }> }) {
  const { versionId } = await ctx.params;
  return NextResponse.json(versionDiff(versionId));
}

