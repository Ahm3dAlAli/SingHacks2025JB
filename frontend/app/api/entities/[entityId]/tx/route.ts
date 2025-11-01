import { NextResponse } from "next/server";
import { listTransactionsForEntity } from "@/lib/mock/transactions";

export async function GET(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  const items = listTransactionsForEntity(entityId, 10);
  return NextResponse.json({ items });
}

