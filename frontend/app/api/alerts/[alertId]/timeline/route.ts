import { NextResponse } from "next/server";
import { loadTransactions } from "@/lib/server/txData";

export async function GET(_: Request, ctx: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await ctx.params;
  const { byId } = await loadTransactions();
  const tx = byId.get(alertId);
  if (!tx) return NextResponse.json([], { status: 200 });
  const createdTs = tx.booking_datetime;
  return NextResponse.json([
    { id: `${alertId}-e1`, ts: createdTs, type: "created", text: `Alert for transaction ${alertId} created` },
    { id: `${alertId}-e2`, ts: createdTs, type: "status", text: "Status set to new" },
  ]);
}
