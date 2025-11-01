import { NextResponse } from "next/server";
import { generateTransaction, evaluateTx } from "@/lib/mock/transactions";

export async function GET(_: Request, ctx: { params: Promise<{ txnId: string }> }) {
  const { txnId } = await ctx.params;
  const tx = generateTransaction(txnId);
  const evaln = evaluateTx(tx);
  return NextResponse.json({ ...tx, evaluation: evaln });
}

