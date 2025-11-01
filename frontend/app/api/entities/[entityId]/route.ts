import { NextResponse } from "next/server";
import { generatePerson } from "@/lib/mock/entities";

export async function GET(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  return NextResponse.json(generatePerson(entityId));
}

