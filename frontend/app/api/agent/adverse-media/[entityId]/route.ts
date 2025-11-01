import { NextResponse } from "next/server";
import { loadTransactions } from "@/lib/server/txData";
import { mockAdverseMediaForName } from "@/lib/server/adverseMedia";

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export async function GET(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  const { rows } = await loadTransactions();
  let name: string | null = null;
  for (const tx of rows) {
    if (tx.originator_name && `n-${slugify(tx.originator_name)}` === entityId) { name = tx.originator_name; break; }
    if (tx.beneficiary_name && `n-${slugify(tx.beneficiary_name)}` === entityId) { name = tx.beneficiary_name; break; }
  }
  if (!name) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const data = mockAdverseMediaForName(name);
  return NextResponse.json({ entityId, name, ...data });
}

