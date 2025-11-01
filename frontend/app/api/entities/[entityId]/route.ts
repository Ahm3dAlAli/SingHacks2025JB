import { NextResponse } from "next/server";
import { loadTransactions } from "@/lib/server/txData";

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
  type Person = { id: string; name: string; nationality: string; dob: string; occupation: string; employer: string; relatives: { relation: string; name: string }[] };
  const idToName = new Map<string, { name: string; country: string }>();
  for (const tx of rows) {
    if (tx.originator_name) idToName.set(`n-${slugify(tx.originator_name)}`, { name: tx.originator_name, country: tx.originator_country || "" });
    if (tx.beneficiary_name) idToName.set(`n-${slugify(tx.beneficiary_name)}`, { name: tx.beneficiary_name, country: tx.beneficiary_country || "" });
  }
  const rec = idToName.get(entityId);
  if (!rec) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const person: Person = {
    id: entityId,
    name: rec.name,
    nationality: rec.country || "—",
    dob: "",
    occupation: "",
    employer: "",
    relatives: [],
  };
  return NextResponse.json(person);
}
